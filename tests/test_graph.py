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
        chain_questions: list[str] = []
        route_histories: list[str] = []
        rewrite_calls: list[tuple[str, str]] = []
        check_calls = 0

    f = Fakes()
    f.chain_calls = []
    f.chain_questions = []
    f.route_histories = []
    f.rewrite_calls = []

    def fake_route(question: str, history: str = "") -> RouteDecision:
        f.route_histories.append(history)
        return RouteDecision(route=f.route, reason="test")

    def fake_rewrite(question: str, history: str) -> str:
        f.rewrite_calls.append((question, history))
        return "REWRITTEN: " + question

    def fake_chain(kind: str, question: str) -> dict:
        f.chain_calls.append(kind)
        f.chain_questions.append(question)
        return make_result(f"answer from {kind} chain")

    def fake_check(question: str, answer: str, context: str) -> GroundingResult:
        ok = f.verdicts[min(f.check_calls, len(f.verdicts) - 1)]
        f.check_calls += 1
        return GroundingResult(grounded=ok, unsupported_claims=[] if ok else ["made up"])

    monkeypatch.setattr(graph, "_decide_route", fake_route)
    monkeypatch.setattr(graph, "_rewrite", fake_rewrite)
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
    assert set(result["latency"]["per_node"]) == {
        "router", "rewrite_question", "policy_rag", "grounding_check"}
    assert result["latency"]["total_seconds"] >= 0


def test_second_turn_in_same_thread_starts_fresh(fakes) -> None:
    thread = new_thread()
    fakes.verdicts = [False]
    graph.run_query("q1", "E1001", thread)  # ends with retry_count 2
    fakes.verdicts = [True]
    fakes.chain_calls.clear()
    result = graph.run_query("q2", "E1001", thread)
    assert fakes.chain_calls == ["normal"] and result["grounded"] is True


def test_first_message_is_not_rewritten(fakes) -> None:
    result = graph.run_query("How many casual leaves?", "E1001", new_thread())
    assert fakes.rewrite_calls == []  # nothing to fill in, so no LLM call
    assert result["rewritten_question"] == "How many casual leaves?"
    assert fakes.chain_questions == ["How many casual leaves?"]


def test_follow_up_is_rewritten_with_the_earlier_chat(fakes) -> None:
    thread = new_thread()
    graph.run_query("What is the work from home rule?", "E1001", thread)
    result = graph.run_query("and for interns?", "E1001", thread)

    question, history = fakes.rewrite_calls[0]
    assert question == "and for interns?"
    assert "Employee: What is the work from home rule?" in history  # the earlier question
    assert "Assistant:" in history  # the earlier answer
    assert "and for interns?" not in history  # the new question is not part of the history
    assert result["rewritten_question"] == "REWRITTEN: and for interns?"
    assert fakes.chain_questions[-1] == "REWRITTEN: and for interns?"  # search used the new text


def test_router_sees_the_earlier_chat_on_a_follow_up(fakes) -> None:
    thread = new_thread()
    graph.run_query("What is the work from home rule?", "E1001", thread)
    graph.run_query("and for interns?", "E1001", thread)
    assert fakes.route_histories[0] == graph.NO_HISTORY
    assert "What is the work from home rule?" in fakes.route_histories[1]


def test_rewrite_runs_only_on_the_policy_route(fakes) -> None:
    thread = new_thread()
    graph.run_query("hello", "E1001", thread)  # builds some history
    for route in ("personal", "sensitive", "out_of_scope"):
        fakes.route = route
        graph.run_query("and now?", "E1001", thread)
    assert fakes.rewrite_calls == []


def test_a_different_thread_has_its_own_memory(fakes) -> None:
    graph.run_query("What is the work from home rule?", "E1001", new_thread())
    graph.run_query("and for interns?", "E1001", new_thread())  # a new chat: no history
    assert fakes.rewrite_calls == []


def test_history_is_cut_and_excludes_the_newest_question() -> None:
    from langchain_core.messages import AIMessage, HumanMessage

    messages = [HumanMessage(content="q1"), AIMessage(content="a" * 1000), HumanMessage(content="q2")]
    history = graph.chat_history({"messages": messages})
    assert [m.content[:2] for m in history] == ["q1", "aa"]
    text = graph.history_to_text(history)
    assert text.startswith("Employee: q1") and len(text) < 400
    assert graph.history_to_text([]) == graph.NO_HISTORY


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
    assert "{" not in graph.REWRITE_PROMPT and "}" not in graph.REWRITE_PROMPT


def test_repeated_citations_of_one_section_are_shown_once() -> None:
    answer = PolicyAnswer(
        answer="x",
        citations=[
            Citation(source="wfh_policy.md", section="2. Hybrid Schedule", quote="3 days in office"),
            Citation(source="wfh_policy.md", section="2. Hybrid Schedule", quote="2 days remote"),
            Citation(source="wfh_policy.md", section="3. Equipment", quote="laptop"),
        ],
        confidence="high", escalate_to_hr=False,
    )
    update = graph._policy_update({"docs": make_docs(), "answer": answer})
    assert [c["section"] for c in update["citations"]] == ["2. Hybrid Schedule", "3. Equipment"]
    assert update["citations"][0]["quote"] == "3 days in office"  # the first one is kept


def test_warm_up_builds_every_chain_without_calling_an_llm(monkeypatch) -> None:
    built: list[str] = []
    monkeypatch.setattr(graph, "get_app", lambda: None)
    monkeypatch.setattr(graph, "_chain", lambda kind: built.append(kind))
    graph.warm_up()
    assert built == ["normal", "strict", "sensitive"]


def test_real_chain_steps_show_up_as_retrieval_and_answer(fakes, monkeypatch) -> None:
    monkeypatch.setattr(graph, "_run_chain", lambda kind, q: {**make_result(), "retrieval_seconds": 0.25, "answer_seconds": 1.5})
    per_node = graph.run_query("q", "E1001", new_thread())["latency"]["per_node"]
    assert per_node["retrieval"] == 0.25 and per_node["answer"] == 1.5
    assert "policy_rag" in per_node  # the whole node is still timed, the report does not count it twice


def test_run_query_logs_numbers_with_a_masked_employee_id_and_no_question(fakes, monkeypatch) -> None:
    records: list[dict] = []
    monkeypatch.setattr(graph, "append_query_log", lambda record, *a, **k: records.append(record))
    graph.run_query("What is my secret question?", "E1001", new_thread())
    assert len(records) == 1
    record = records[0]
    assert record["employee"] == "E1***" and record["route"] == "policy"
    assert record["question_chars"] == len("What is my secret question?")
    assert "secret" not in str(record) and "E1001" not in str(record)  # no question text, no real ID
    assert "router" in record["per_node_seconds"] and record["total_seconds"] >= 0


def test_run_query_can_skip_the_log(fakes, monkeypatch) -> None:
    records: list[dict] = []
    monkeypatch.setattr(graph, "append_query_log", lambda record, *a, **k: records.append(record))
    graph.run_query("q", "E1001", new_thread(), log=False)
    assert records == []