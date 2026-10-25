"""Tests for src/app_support.py (the helpers behind the Streamlit app)."""
import json

import pytest

from src import app_support


def test_users_come_from_the_hrms_file() -> None:
    users = app_support.load_users()
    assert users["E1001"] == "Asha Patil"
    assert "I2001" in users  # the intern is in the list too


def test_dropdown_label_shows_id_and_name() -> None:
    assert app_support.user_label("E1001", {"E1001": "Asha Patil"}) == "E1001 - Asha Patil"


def test_llm_label_reads_the_env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-20b")
    assert app_support.llm_label() == "groq / openai/gpt-oss-20b"


def test_new_thread_ids_are_different() -> None:
    assert app_support.new_thread_id() != app_support.new_thread_id()


def test_feedback_is_appended_one_json_line_each(tmp_path) -> None:
    file = tmp_path / "feedback.jsonl"
    app_support.append_feedback("q1", "a1", "up", "policy", path=file)
    app_support.append_feedback("q2", "a2 ₹", "down", "personal", path=file)
    rows = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert set(rows[0]) == {"timestamp", "question", "answer", "rating", "route"}
    assert rows[1]["rating"] == "down" and rows[1]["answer"] == "a2 ₹"


def test_bad_rating_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        app_support.append_feedback("q", "a", "meh", "policy", path=tmp_path / "f.jsonl")