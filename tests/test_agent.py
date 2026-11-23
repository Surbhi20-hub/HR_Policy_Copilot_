"""Tests for the optional ReAct agent. No LLM and no internet: the agent and the final LLM step are fakes."""
import itertools

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

from src import agent, graph
from src.schemas import Citation, GroundingResult, PolicyAnswer, RouteDecision

counter = itertools.count()


def new_thread() -> str:
    return f"agent-test-{next(counter)}"


def policy_docs() -> list[Document]:
    return [Document(
        page_content="## 3. Casual Leave (CL)\n- Employees get 8 days of casual leave per year.",
        metadata={"source": "leave_policy.md", "section": "3. Casual Leave (CL)",
                  "section_number": "3", "policy_effective_date": "2026-04-01"},
    )]


def make_answer(text: str = "You get 8 days of casual leave.") -> PolicyAnswer:
    return PolicyAnswer(
        answer=text,
        citations=[Citation(source="leave_policy.md", section="3. Casual Leave (CL)",
                            quote="Employees get 8 days of casual leave per year.")],
        confidence="high", escalate_to_hr=False,
    )


class GreedyAgent:
    """Pretends to be a model that never stops calling its tools (10 rounds of 2 calls)."""

    def __init__(self, tools: list, rounds: int = 10) -> None:
        self.tools = {t.name: t for t in tools}
        self.rounds = rounds

    def invoke(self, inputs: dict, config: dict | None = None) -> dict:
        for number in range(self.rounds):
            self.tools["policy_search"].invoke({"query": f"casual leave {number}"})
            self.tools["get_leave_balance"].invoke({})
        return {"messages": [AIMessage(content="draft answer")]}


def use_fake_agent(monkeypatch: pytest.MonkeyPatch, docs: list[Document], agent_class=GreedyAgent) -> None:
    monkeypatch.setattr(agent, "_policy_retriever", lambda: RunnableLambda(lambda q: docs))
    monkeypatch.setattr(agent, "_build_agent", lambda tools: agent_class(tools))


# ---------------------------------------------------------------- switch is off by default

def test_agent_mode_is_off_by_default_and_the_normal_graph_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_MODE", raising=False)
    assert agent.agent_mode_on() is False and agent.mode_label() == "Standard"
    nodes = set(graph.build_graph().get_graph().nodes)
    assert {"policy_rag", "tool", "grounding_check"} <= nodes and "agent" not in nodes


def test_agent_mode_true_swaps_policy_rag_and_tool_for_the_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MODE", "true")
    assert agent.agent_mode_on() is True and agent.mode_label() == "Agent"
    nodes = set(graph.build_graph().get_graph().nodes)
    assert "agent" in nodes and "policy_rag" not in nodes and "tool" not in nodes
    assert {"sensitive", "out_of_scope", "grounding_check"} <= nodes


# ---------------------------------------------------------------- the tools

def test_leave_tool_takes_no_employee_id_and_uses_the_logged_in_user() -> None:
    box = agent.ToolBox("E1003", retriever=RunnableLambda(lambda q: []))
    tools = {t.name: t for t in agent.make_tools(box)}
    assert "employee_id" not in tools["get_leave_balance"].args  # the model has no way to choose a person
    text = tools["get_leave_balance"].invoke({})
    assert "Neha" in text and "Asha" not in text
    assert box.evidence[0].metadata["source"] == "hrms_mock.json"


def test_graph_gives_the_agent_the_sidebar_employee_not_the_one_in_the_text(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_run_agent(question: str, employee_id: str, strict: bool) -> dict:
        seen["employee_id"] = employee_id
        return {"question": question, "docs": policy_docs(), "answer": make_answer(), "tools_called": ["get_leave_balance"]}

    monkeypatch.setattr(graph, "_decide_route", lambda question, history="": RouteDecision(route="personal", reason="t"))
    monkeypatch.setattr(graph, "_run_agent", fake_run_agent)
    monkeypatch.setattr(graph, "_check_grounding", lambda q, a, c: GroundingResult(grounded=True, unsupported_claims=[]))
    monkeypatch.setattr(graph, "get_app", lambda: graph.build_graph(agent_mode=True))
    result = graph.run_query("What is E1003's leave balance?", "E1001", new_thread(), log=False)
    assert seen["employee_id"] == "E1001"
    assert result["tools_called"] == ["get_leave_balance"] and result["route"] == "personal"


# ---------------------------------------------------------------- limits and refusal

def test_agent_never_makes_more_than_5_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake_agent(monkeypatch, policy_docs())
    monkeypatch.setattr(agent, "_finalize_answer", lambda q, c, n, s: make_answer())
    result = agent.run_agent("Can I take 3 days of casual leave next week?", "E1001")
    assert agent.MAX_TOOL_CALLS == 5
    assert len(result["tools_called"]) == 5  # 20 calls were tried, 5 were allowed


def test_tools_stop_working_after_the_limit() -> None:
    box = agent.ToolBox("E1001", retriever=RunnableLambda(lambda q: policy_docs()), max_calls=2)
    box.policy_search("a")
    box.policy_search("b")
    assert agent.LIMIT_MESSAGE == box.policy_search("c") == box.leave_balance()
    assert box.calls == ["policy_search", "policy_search"]


def test_a_question_the_tools_cannot_answer_returns_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    class OneSearch:
        def __init__(self, tools: list) -> None:
            self.tools = {t.name: t for t in tools}

        def invoke(self, inputs: dict, config: dict | None = None) -> dict:
            self.tools["policy_search"].invoke({"query": "stock option vesting"})
            return {"messages": [AIMessage(content="nothing found")]}

    def must_not_run(*args) -> PolicyAnswer:
        raise AssertionError("the LLM must not write an answer when the tools found nothing")

    use_fake_agent(monkeypatch, [], OneSearch)  # the search finds no chunk
    monkeypatch.setattr(agent, "_finalize_answer", must_not_run)
    result = agent.run_agent("What is the stock option vesting schedule?", "E1001")
    answer = result["answer"]
    assert answer.citations == [] and answer.escalate_to_hr is True and answer.confidence == "low"
    assert "hr@company.com" in answer.answer and result["tools_called"] == ["policy_search"]


# ---------------------------------------------------------------- the grounding check still applies

def test_agent_answer_still_goes_through_grounding_with_one_retry_and_the_same_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def fake_run_agent(question: str, employee_id: str, strict: bool) -> dict:
        calls.append(strict)
        return {"question": question, "docs": policy_docs(), "answer": make_answer(), "tools_called": ["policy_search"]}

    monkeypatch.setattr(graph, "_decide_route", lambda question, history="": RouteDecision(route="policy", reason="t"))
    monkeypatch.setattr(graph, "_run_agent", fake_run_agent)
    monkeypatch.setattr(graph, "_check_grounding", lambda q, a, c: GroundingResult(grounded=False, unsupported_claims=["made up"]))
    monkeypatch.setattr(graph, "get_app", lambda: graph.build_graph(agent_mode=True))
    result = graph.run_query("How many casual leaves?", "E1001", new_thread(), log=False)
    assert calls == [False, True]  # normal first, then one strict retry
    assert result["answer"] == graph.FALLBACK_ANSWER and result["citations"] == []


def test_sensitive_and_out_of_scope_stay_as_they_are_in_agent_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"chain": 0, "agent": 0}

    def fake_chain(kind: str, question: str) -> dict:
        called["chain"] += 1
        return {"question": question, "docs": policy_docs(), "answer": make_answer("Please contact HR.")}

    def fake_run_agent(*args) -> dict:
        called["agent"] += 1
        raise AssertionError("the agent must not handle this route")

    monkeypatch.setattr(graph, "_run_chain", fake_chain)
    monkeypatch.setattr(graph, "_run_agent", fake_run_agent)
    monkeypatch.setattr(graph, "get_app", lambda: graph.build_graph(agent_mode=True))
    for route in ("sensitive", "out_of_scope"):
        monkeypatch.setattr(graph, "_decide_route", lambda question, history="", r=route: RouteDecision(route=r, reason="t"))
        result = graph.run_query("question", "E1001", new_thread(), log=False)
        assert result["route"] == route and result["tools_called"] == []
    assert called == {"chain": 1, "agent": 0}  # only the sensitive route used the chain


def test_steps_are_printed_as_act_and_observe() -> None:
    messages = [
        AIMessage(content="", tool_calls=[{"name": "policy_search", "args": {"query": "carry forward"}, "id": "1"}]),
        ToolMessage(content="[Chunk 1] source: leave_policy.md", tool_call_id="1"),
        AIMessage(content="You can carry forward 10 days."),
    ]
    lines = agent.steps_from(messages)
    assert lines[0].startswith("ACT") and "policy_search" in lines[0]
    assert lines[1].startswith("OBSERVE") and lines[2].startswith("REASON")