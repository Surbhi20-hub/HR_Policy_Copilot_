"""Tests for the router and the leave-balance tool.

Part A asks the REAL LLM (3 tiny calls, free). It is skipped if no key is set.
Parts B and C need no LLM and no internet.
"""
import itertools
import os

import pytest

from src import graph
from src.schemas import RouteDecision
from src.tools import get_leave_balance

PROVIDER_KEYS = {"groq": "GROQ_API_KEY", "google_genai": "GOOGLE_API_KEY"}
counter = itertools.count()


def llm_key_is_missing() -> bool:
    """True if the chosen provider needs an API key and .env does not have it."""
    key_name = PROVIDER_KEYS.get(os.getenv("LLM_PROVIDER", "groq"))
    return bool(key_name) and not os.getenv(key_name)


needs_llm = pytest.mark.skipif(llm_key_is_missing(), reason="no LLM API key in .env")


# ---------------------------------------------------------------- A. the router (real LLM)

@needs_llm
@pytest.mark.parametrize(
    ("question", "expected_route"),
    [
        ("What is my leave balance?", "personal"),
        ("What is the CEO salary?", "out_of_scope"),
        ("My manager keeps harassing me and I feel unsafe. What can I do?", "sensitive"),
    ],
)
def test_router_picks_the_right_route(question: str, expected_route: str) -> None:
    decision = graph._decide_route(question)
    assert decision.route == expected_route, decision.reason


# ---------------------------------------------------------------- B. personal question = tool only

def test_personal_question_calls_the_tool_and_never_the_retriever(monkeypatch) -> None:
    calls: list[dict] = []
    real_tool = graph.get_leave_balance

    class SpyTool:
        """Wraps the real tool and remembers how it was called."""

        def invoke(self, arguments: dict) -> dict:
            calls.append(arguments)
            return real_tool.invoke(arguments)

    class FailIfCalled:
        """Stands in for the retriever and fails the test if anybody uses it."""

        def __call__(self, *args, **kwargs):
            raise AssertionError("The retriever was called for a personal question!")

    def fail_run_chain(*args, **kwargs):
        raise AssertionError("The RAG chain was called for a personal question!")

    monkeypatch.setattr(graph, "_decide_route",
                        lambda question: RouteDecision(route="personal", reason="test"))
    monkeypatch.setattr(graph, "get_leave_balance", SpyTool())
    monkeypatch.setattr(graph, "_run_chain", fail_run_chain)
    monkeypatch.setattr("src.rag_chain.get_hybrid_retriever", FailIfCalled())
    monkeypatch.setattr("src.retriever.get_vector_retriever", FailIfCalled())
    monkeypatch.setattr("src.retriever.get_bm25_retriever", FailIfCalled())

    result = graph.run_query("How many leaves do I have left?", "E1001", f"router-tool-{next(counter)}")

    assert calls == [{"employee_id": "E1001"}]  # exactly one call, ID taken from state
    assert result["route"] == "personal"
    assert "12.5 days" in result["answer"]
    assert set(result["latency"]["per_node"]) == {"router", "tool"}  # no policy_rag node


# ---------------------------------------------------------------- C. the tool itself

def test_unknown_employee_returns_an_error() -> None:
    result = get_leave_balance.invoke({"employee_id": "E9999"})
    assert result == {"error": "Employee E9999 not found"}


def test_known_employee_returns_the_record() -> None:
    result = get_leave_balance.invoke({"employee_id": "E1001"})
    assert result["name"] == "Asha Patil" and result["PL"] == 12.5