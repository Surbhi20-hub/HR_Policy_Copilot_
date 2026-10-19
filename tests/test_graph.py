"""Tests for src/graph.py. The LLM calls are replaced by fakes, so no key or internet is needed."""
import itertools

import pytest
from langchain_core.documents import Document

from src import graph
from src.schemas import Citation, GroundingResult, PolicyAnswer, RouteDecision

counter = itertools.count()


def new_thread() -> str:
    """A fresh chat id for every test."""
    return f"test-{next(counter)}"


def make_docs() -> list[Document]:
    return [Document(
        page_content="## 3. Casual Leave (CL)\n- Employees get 8 days of casual leave per year.",
        metadata={"source": "leave_policy.md", "section": "3. Casual Leave (CL)",
                  "policy_effective_date": "2026-04-01"},
    )]


def make_result(text: str = "You get 8 days of casual leave.") -> dict:
    answer = PolicyAnswer(
        answer=text,
        citations=[Citation(source="leave_policy.md", section="3. Casual Leave (CL)",
                            quote="Employees get 8 days of casual leave per year.")],
        confidence="high", escalate_to_hr=False,
    )
    return {"question": "q", "docs": make_docs(), "answer": answer}


@pytest.fixture
def fakes(monkeypatch):
    """Fake router, chain and checker. Tests change fakes.route / fakes.verdicts."""
    class Fakes:
        route = "policy"
        verdicts = [True]  # one grounded verdict per check (the last one repeats)
        chain_calls: list[str] = []
        check_calls = 0

    f = Fakes()
    f.chain_calls = []

    def fake_route(question: str) -> RouteDecision:
        return RouteDecision(route=f.route, reason="test")

    def fake_chain(kind: str, question: str) -> dict:
        f.chain_calls.append(kind)
        return make_result(f"answer from {kind} chain")

    def fake_check(question: str, answer: str, context: str) -> GroundingResult:
        ok = f.verdicts[min(f.check_calls, len(f.verdicts) - 1)]
        f.check_calls += 1
        return GroundingResult(grounded=ok, unsupported_claims=[] if ok else ["made up"])

    monkeypatch.setattr(graph, "_decide_route", fake_route)
    monkeypatch.setattr(graph, "_run_chain", fake_chain)
    monkeypatch.setattr(graph, "_check_grounding", fake_check)
    return f


def test_policy_route_answers_with_citation(fakes) -> None:
    result = graph.run_query("How many casual leaves?", "E1001", new_thread())
    assert result["route"] == "policy" and result["grounded"] is True
    assert result["answer"] == "answer from normal chain"
    assert result["citations"][0]["section"] == "3. Casual Leave (CL)"
    assert fakes.chain_calls == ["normal"]


def test_not_grounded_retries_once_with_strict_rules(fakes) -> None:
    fakes.verdicts = [False, True]
    result = graph.run_query("q", "E1001", new_thread())
    assert fakes.chain_calls == ["normal", "strict"]
    assert result["answer"] == "answer from strict chain" and result["grounded"] is True


def test_still_not_grounded_gives_fallback_after_one_retry(fakes) -> None:
    fakes.verdicts = [False]
    result = graph.run_query("q", "E1001", new_thread())
    assert fakes.chain_calls == ["normal", "strict"]  # exactly one retry
    assert result["answer"] == graph.FALLBACK_ANSWER
    assert result["citations"] == [] and result["escalate_to_hr"] is True


def test_made_up_quote_fails_grounding(fakes, monkeypatch) -> None:
    bad = make_result()
    bad["answer"].citations[0].quote = "Employees get 99 days of leave"
    monkeypatch.setattr(graph, "_run_chain", lambda kind, q: bad)
    result = graph.run_query("q", "E1001", new_thread())  # the fake checker says OK, the quote check says no
    assert result["answer"] == graph.FALLBACK_ANSWER


def test_personal_route_uses_employee_id_from_state_not_from_text(fakes) -> None:
    fakes.route = "personal"
    result = graph.run_query("What is E1003's leave balance?", "E1001", new_thread())
    assert "Asha" in result["answer"] and "12.5 days" in result["answer"]
    assert "Neha" not in result["answer"]
    assert fakes.chain_calls == []  # no RAG for personal data


def test_intern_gets_intern_leave(fakes) -> None:
    fakes.route = "personal"
    result = graph.run_query("my balance", "I2001", new_thread())
    assert "Karan" in result["answer"] and "2 days of intern leave" in result["answer"]


def test_unknown_employee_is_handled(fakes) -> None:
    fakes.route = "personal"
    result = graph.run_query("my balance", "E9999", new_thread())
    assert "couldn't find employee E9999" in result["answer"]
    assert result["escalate_to_hr"] is True


def test_missing_employee_id_is_handled(fakes) -> None:
    fakes.route = "personal"
    assert "don't know which employee" in graph.run_query("my balance", "", new_thread())["answer"]


def test_out_of_scope_refuses_without_any_llm_call(fakes) -> None:
    fakes.route = "out_of_scope"
    result = graph.run_query("What is the CEO's salary?", "E1001", new_thread())
    assert result["answer"] == graph.OUT_OF_SCOPE_ANSWER
    assert fakes.chain_calls == [] and fakes.check_calls == 0


def test_sensitive_always_escalates(fakes) -> None:
    fakes.route = "sensitive"
    result = graph.run_query("I am being harassed", "E1001", new_thread())
    assert fakes.chain_calls == ["sensitive"] and result["escalate_to_hr"] is True


def test_latency_is_reported_per_node_and_total(fakes) -> None:
    result = graph.run_query("q", "E1001", new_thread())
    assert set(result["latency"]["per_node"]) == {"router", "policy_rag", "grounding_check"}
    assert result["latency"]["total_seconds"] >= 0


def test_second_turn_in_same_thread_starts_fresh(fakes) -> None:
    thread = new_thread()
    fakes.verdicts = [False]
    graph.run_query("q1", "E1001", thread)  # ends with retry_count 2
    fakes.verdicts = [True]
    fakes.chain_calls.clear()
    result = graph.run_query("q2", "E1001", thread)
    assert fakes.chain_calls == ["normal"] and result["grounded"] is True


def test_quote_check_ignores_punctuation_and_case() -> None:
    context = "- Gifts above INR 2,000 must be declared."
    assert graph.quote_is_in_context("gifts above INR 2,000 must be declared", context)
    assert not graph.quote_is_in_context("gifts above INR 5,000 must be declared", context)


def test_leave_text_for_probation_and_singular_day() -> None:
    text = graph.format_leave_balance(
        {"name": "Rohan Mehta", "PL": 1, "CL": 6, "SL": 10, "on_probation": True})
    assert "PL) 1 day," in text and "probation" in text


def test_router_prompt_has_no_stray_braces() -> None:
    assert "{" not in graph.ROUTER_PROMPT and "}" not in graph.ROUTER_PROMPT
    assert "{" not in graph.GROUNDING_PROMPT and "{" not in graph.SENSITIVE_RULES