"""The real chain must report how long the search and the answer took (no LLM or index needed)."""
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from src import rag_chain
from src.schemas import Citation, PolicyAnswer


class FakeLLM:
    """Stands in for the chat model: with_structured_output(...).with_retry(...) gives a fixed answer."""

    def with_structured_output(self, schema):
        return RunnableLambda(lambda prompt_value: PolicyAnswer(
            answer="8 days", citations=[Citation(source="leave_policy.md", section="3. Casual Leave (CL)",
                                                 quote="8 days per year")],
            confidence="high", escalate_to_hr=False))

    def with_retry(self, **kwargs):
        return self


def test_chain_returns_docs_answer_and_both_step_times(monkeypatch) -> None:
    doc = Document(page_content="## 3. Casual Leave (CL)\n8 days per year.",
                   metadata={"source": "leave_policy.md", "section": "3. Casual Leave (CL)",
                             "section_number": "3", "policy_effective_date": "2026-04-01"})
    monkeypatch.setattr(rag_chain, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(rag_chain, "get_hybrid_retriever", lambda k: RunnableLambda(lambda question: [doc]))
    result = rag_chain.build_rag_chain().invoke("How many casual leaves?")
    assert result["question"] == "How many casual leaves?" and result["docs"] == [doc]
    assert result["answer"].answer == "8 days"
    assert result["retrieval_seconds"] >= 0 and result["answer_seconds"] >= 0