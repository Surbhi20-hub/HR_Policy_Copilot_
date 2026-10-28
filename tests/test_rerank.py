"""Tests for the cross-encoder re-ranker. A fake scorer is used, so no model is downloaded."""
import importlib.util
import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from src import retriever
from src.retriever import get_reranked_retriever, rerank_docs

ROOT = Path(__file__).resolve().parent.parent


def load_compare_module():
    """Import eval/compare_rerank.py (the eval folder is not a package)."""
    spec = importlib.util.spec_from_file_location("compare_rerank", ROOT / "eval" / "compare_rerank.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["compare_rerank"] = module
    spec.loader.exec_module(module)
    return module


def make_doc(text: str, number: str) -> Document:
    return Document(page_content=text, metadata={"source": "leave_policy.md", "section": f"S{number}", "section_number": number})


def fake_scorer(pairs: list[tuple[str, str]]) -> list[float]:
    """Pretend the chunk that contains the word 'carry' is the best match."""
    return [10.0 if "carry" in text else 0.0 for _, text in pairs]


def test_rerank_puts_the_best_chunk_first_and_keeps_k() -> None:
    docs = [make_doc("sick leave", "1"), make_doc("carry forward rules", "2"), make_doc("holidays", "3")]
    result = rerank_docs("carry forward?", docs, fake_scorer, k=2)
    assert [d.metadata["section_number"] for d in result] == ["2", "1"]  # ties keep the old order


def test_rerank_with_no_docs_returns_empty() -> None:
    assert rerank_docs("anything", [], fake_scorer, k=5) == []


def test_reranked_retriever_asks_hybrid_for_more_then_cuts(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = {}

    def fake_hybrid(k: int):
        asked["k"] = k
        return RunnableLambda(lambda q: [make_doc("a", "1"), make_doc("carry on", "2"), make_doc("b", "3")])

    monkeypatch.setattr(retriever, "get_hybrid_retriever", fake_hybrid)
    result = get_reranked_retriever(k=1, fetch_k=20, scorer=fake_scorer).invoke("q")
    assert asked["k"] == 20
    assert [d.metadata["section_number"] for d in result] == ["2"]


def test_compare_counts_ranks_and_changes() -> None:
    module = load_compare_module()
    questions = [{"id": 1, "question": "q1", "source": "leave_policy.md#2"}]
    docs_before = [make_doc("x", "1"), make_doc("y", "3"), make_doc("z", "2")]  # right one is 3rd
    docs_after = [make_doc("z", "2"), make_doc("x", "1")]  # right one is 1st
    result = module.compare(questions, lambda q: docs_before, lambda q: docs_after)
    assert result["before"]["hit@1"] == 0 and result["before"]["hit@3"] == 1
    assert result["after"]["hit@1"] == 1 and result["after"]["mrr"] == 1.0
    assert "better" in module.build_report(result, "fake-model", "2026-10-28")


def test_usable_questions_skips_unanswerable_and_personal() -> None:
    module = load_compare_module()
    golden = [
        {"id": 1, "source": "leave_policy.md#2", "answerable": True, "type": "policy"},
        {"id": 2, "source": None, "answerable": False, "type": "policy"},
        {"id": 3, "source": "hrms", "answerable": True, "type": "personal"},
    ]
    assert [q["id"] for q in module.usable_questions(golden)] == [1]


def test_graph_default_mode_is_hybrid_and_rerank_is_allowed() -> None:
    from src import graph

    assert graph.RETRIEVER_MODE in graph.RETRIEVER_MODES
    graph.set_retriever_mode("rerank")
    graph.set_retriever_mode("hybrid")
    with pytest.raises(ValueError):
        graph.set_retriever_mode("magic")