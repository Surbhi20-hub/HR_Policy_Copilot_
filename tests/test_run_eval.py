"""Tests for eval/run_eval.py (no LLM and no internet: the copilot and the judge are faked)."""
import json

import pytest

from eval import run_eval as ev

CHUNKS = [
    {"source": "leave_policy.md", "section": "2. Privilege Leave", "section_number": "2", "text": "18 days."},
    {"source": "wfh_policy.md", "section": "1. Eligibility", "section_number": "1", "text": "After probation."},
]


def test_hit_in_top5_matches_file_and_section_number() -> None:
    assert ev.hit_in_top5("leave_policy.md#2", CHUNKS) is True
    assert ev.hit_in_top5("leave_policy.md#3", CHUNKS) is False  # right file, wrong section
    assert ev.hit_in_top5("expense_policy.md#2", CHUNKS) is False
    assert ev.hit_in_top5(None, CHUNKS) is None  # skipped for unanswerable questions


def test_hit_in_top5_ignores_the_sixth_chunk() -> None:
    filler = [{"source": "x.md", "section": "1. A", "section_number": "1", "text": ""}] * 5
    assert ev.hit_in_top5("leave_policy.md#2", filler + CHUNKS) is False


def test_percentile_and_cost() -> None:
    assert ev.percentile([1, 2, 3, 4, 100], 95) == 100
    assert ev.percentile([], 95) == 0.0
    assert ev.estimate_cost(None) == 0.0
    cost = ev.estimate_cost({"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    assert cost == pytest.approx(ev.PRICE_INPUT_PER_M + ev.PRICE_OUTPUT_PER_M)


def fake_result(route: str = "policy", citations: int = 1, chunks: list | None = None) -> dict:
    return {"answer": "18 days", "route": route, "citations": [{"source": "a"}] * citations,
            "retrieved": CHUNKS if chunks is None else chunks, "latency": {"total_seconds": 2.0, "per_node": {"router": 0.5, "policy_rag": 1.0, "retrieval": 0.2, "answer": 0.8}},
            "tokens": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100}}


def test_answerable_policy_row(monkeypatch) -> None:
    monkeypatch.setattr(ev, "ask_copilot", lambda q, e, t: fake_result())
    monkeypatch.setattr(ev, "judge_correct", lambda q, e, a: ev.CorrectnessVerdict(correct=True, reason="ok"))
    monkeypatch.setattr(ev, "judge_faithful", lambda a, c: ev.FaithfulnessVerdict(faithful=True, reason="ok"))
    item = {"id": 1, "question": "q", "expected": "18", "source": "leave_policy.md#2",
            "answerable": True, "type": "policy"}
    row = ev.evaluate_item(item, "t1", ev.WaitClock())
    assert row["correct"] is True and row["hit"] is True and row["citation_ok"] is True
    assert row["faithful"] is True and row["refused"] is None
    assert ev.failure_reasons(row) == []


def test_personal_row_skips_hit_and_faithfulness(monkeypatch) -> None:
    monkeypatch.setattr(ev, "ask_copilot", lambda q, e, t: fake_result("personal", 0, []))
    monkeypatch.setattr(ev, "judge_correct", lambda q, e, a: ev.CorrectnessVerdict(correct=True, reason="ok"))
    item = {"id": 28, "question": "q", "expected": "x", "source": None, "answerable": True,
            "type": "personal", "employee_id": "E1001"}
    row = ev.evaluate_item(item, "t1", ev.WaitClock())
    assert row["hit"] is None and row["faithful"] is None and row["citation_ok"] is None


def test_unanswerable_row_is_judged_on_refusal(monkeypatch) -> None:
    monkeypatch.setattr(ev, "ask_copilot", lambda q, e, t: fake_result("out_of_scope", 0, []))
    monkeypatch.setattr(ev, "judge_refusal", lambda q, e, a: ev.RefusalVerdict(refused=False, reason="gave a number"))
    item = {"id": 12, "question": "q", "expected": "REFUSE - x", "source": None,
            "answerable": False, "type": "policy"}
    row = ev.evaluate_item(item, "t1", ev.WaitClock())
    assert row["refused"] is False and row["hit"] is None
    assert "should have refused" in ev.failure_reasons(row)[0]


def test_backoff_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(ev.time, "sleep", lambda s: None)
    monkeypatch.setattr(ev, "RETRY_WAITS", (5, 5))
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 rate limit")
        return "ok"

    clock = ev.WaitClock()
    assert ev.with_backoff(flaky, clock, "test") == "ok"
    assert clock.seconds >= 10  # both pauses counted as waiting


def test_backoff_gives_up(monkeypatch) -> None:
    monkeypatch.setattr(ev.time, "sleep", lambda s: None)
    monkeypatch.setattr(ev, "RETRY_WAITS", (1,))
    with pytest.raises(RuntimeError):
        ev.with_backoff(lambda: (_ for _ in ()).throw(RuntimeError("boom")), ev.WaitClock(), "t")


def test_summarize_and_report(monkeypatch, tmp_path) -> None:
    rows = [
        {"id": 1, "question": "a", "type": "policy", "answerable": True, "expected": "e", "source": "s#1",
         "correct": True, "refused": None, "faithful": True, "hit": True, "citation_ok": True,
         "latency_seconds": 2.0, "tokens": {"total_tokens": 100}, "cost_usd": 0.001, "wait_seconds": 4},
        {"id": 2, "question": "b", "type": "policy", "answerable": True, "expected": "e", "source": "s#1",
         "correct": False, "correct_reason": "wrong number", "refused": None, "faithful": False,
         "unsupported": ["x"], "hit": False, "citation_ok": False, "route": "policy", "answer": "z",
         "latency_seconds": 4.0, "tokens": {"total_tokens": 300}, "cost_usd": 0.003, "wait_seconds": 0},
        {"id": 3, "question": "c", "type": "policy", "answerable": False, "expected": "REFUSE", "source": None,
         "correct": None, "refused": True, "faithful": None, "hit": None, "citation_ok": None,
         "latency_seconds": 1.0, "tokens": None, "cost_usd": 0.0, "wait_seconds": 0},
    ]
    stats = ev.summarize(rows)
    assert stats["correctness"] == (1, 2) and stats["refusal"] == (1, 1)
    assert stats["hit_rate"] == (1, 2) and stats["latency_avg"] == pytest.approx(7 / 3)
    assert stats["wait_total"] == 4

    monkeypatch.setattr(ev, "EVAL_DIR", tmp_path)
    meta = {"date": "2026-10-26", "llm": "l", "judge": "j"}
    ev.save_results("hybrid", meta, rows)
    report = ev.build_report()
    assert "Metrics - hybrid" in report and "Failed questions - hybrid (1)" in report
    assert "Not ready yet" in report  # the vector run is missing
    assert json.loads((tmp_path / "results_hybrid.json").read_text(encoding="utf-8"))["rows"][0]["id"] == 1


def test_report_includes_hand_written_failure_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ev, "EVAL_DIR", tmp_path)
    (tmp_path / "failure_analysis.md").write_text("## Failure analysis\n\nMy notes.", encoding="utf-8")
    assert "My notes." in ev.build_report()


def test_step_seconds_does_not_count_parent_nodes_twice() -> None:
    per_node = {"router": 1.0, "policy_rag": 3.0, "retrieval": 0.5, "answer": 2.5, "grounding_check": 1.0}
    assert ev.step_seconds(per_node) == {"router": 1.0, "retrieval": 0.5, "answer": 2.5, "grounding_check": 1.0}
    assert ev.step_seconds({"router": 1.0, "tool": 0.1}) == {"router": 1.0, "tool": 0.1}


def test_slowest_steps_are_averaged_and_sorted() -> None:
    rows = [
        {"per_node": {"router": 1.0, "retrieval": 0.5, "answer": 4.0}},
        {"per_node": {"router": 3.0, "retrieval": 0.5, "answer": 8.0}},
        {"per_node": {"router": 9.0}, "error": "boom"},  # error rows are ignored
        {"id": 9},  # old rows without timing are ignored
    ]
    assert ev.slowest_steps(rows, count=2) == [("answer", 6.0), ("router", 2.0)]
    assert ev.slowest_steps([{"id": 1}]) == []


def _timed_row(latency: float) -> dict:
    return {"id": 1, "question": "q", "type": "policy", "answerable": True, "expected": "e", "source": "s#1",
            "correct": True, "refused": None, "faithful": True, "hit": True, "citation_ok": True,
            "route": "policy", "answer": "a", "latency_seconds": latency, "wait_seconds": 30,
            "per_node": {"router": 1.0, "policy_rag": latency - 1, "retrieval": 0.5, "answer": latency - 1.5},
            "tokens": {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200}, "cost_usd": 0.0001}


def test_report_shows_slowest_steps_only_when_over_the_target(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ev, "EVAL_DIR", tmp_path)
    meta = {"date": "2026-10-27", "llm": "l", "judge": "j", "prices": [0.1, 0.4]}
    ev.save_results("hybrid", meta, [_timed_row(12.0)])
    slow = ev.build_report()
    assert "The 3 slowest steps" in slow and "**answer**" in slow
    assert "Lower k" in slow or "Shorter context" in slow
    assert "Free-tier waiting (NOT in latency) | 30 s" in slow
    assert "ESTIMATED" in slow and "Rs 0" in slow and "$0.1 in / $0.4 out" in slow
    assert "1,200 (1,000 in + 200 out)" in slow

    ev.save_results("hybrid", meta, [_timed_row(4.0)])
    fast = ev.build_report()
    assert "slowest steps" not in fast and "Where the time goes" in fast