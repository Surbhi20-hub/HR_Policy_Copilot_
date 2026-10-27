"""Tests for src/query_log.py (masking, price table, the log file)."""
import json

import pytest

from src import query_log


def test_mask_employee_id_keeps_two_characters() -> None:
    assert query_log.mask_employee_id("E1001") == "E1***"
    assert query_log.mask_employee_id("I2001") == "I2***"
    assert query_log.mask_employee_id("") == ""


def test_price_table_known_model_unknown_model_and_env_override(monkeypatch) -> None:
    monkeypatch.delenv("COST_INPUT_PER_M", raising=False)
    monkeypatch.delenv("COST_OUTPUT_PER_M", raising=False)
    assert query_log.price_for("openai/gpt-oss-20b") == (0.075, 0.30)
    assert query_log.price_for("some-new-model") == query_log.DEFAULT_PRICE
    monkeypatch.setenv("COST_INPUT_PER_M", "1.0")
    assert query_log.price_for("openai/gpt-oss-20b") == (1.0, 0.30)


def test_estimate_cost(monkeypatch) -> None:
    monkeypatch.delenv("COST_INPUT_PER_M", raising=False)
    monkeypatch.delenv("COST_OUTPUT_PER_M", raising=False)
    tokens = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert query_log.estimate_cost(tokens, "openai/gpt-oss-20b") == pytest.approx(0.075 + 0.30)
    assert query_log.estimate_cost(None, "openai/gpt-oss-20b") == 0.0


def test_append_query_log_writes_one_json_line_each_time(tmp_path) -> None:
    path = tmp_path / "logs" / "queries.jsonl"  # the folder does not exist yet
    assert query_log.append_query_log({"route": "policy", "total_seconds": 1.5}, path) is True
    assert query_log.append_query_log({"route": "personal"}, path) is True
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["route"] for line in lines] == ["policy", "personal"]
    assert "timestamp" in json.loads(lines[0])


def test_append_query_log_never_crashes_the_app(tmp_path) -> None:
    blocker = tmp_path / "file.txt"
    blocker.write_text("x", encoding="utf-8")
    assert query_log.append_query_log({"a": 1}, blocker / "sub" / "q.jsonl") is False  # cannot make a folder inside a file