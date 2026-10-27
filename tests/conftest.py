"""Shared test setup: no test may write to the real logs/queries.jsonl."""
import pytest


@pytest.fixture(autouse=True)
def no_query_log(monkeypatch) -> None:
    """run_query() logs every query. Tests replace that with a do-nothing function."""
    monkeypatch.setattr("src.graph.append_query_log", lambda record, *args, **kwargs: True)