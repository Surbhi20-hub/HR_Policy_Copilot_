"""Tests for src/schemas.py and the context formatting in src/rag_chain.py (no LLM needed)."""
import pytest
from langchain_core.documents import Document
from pydantic import ValidationError

from src.rag_chain import STRICT_RULES, SYSTEM_PROMPT, format_context
from src.schemas import Citation, PolicyAnswer


def make_citation(quote: str = "short quote") -> Citation:
    """Helper: build a valid citation."""
    return Citation(source="leave_policy.md", section="4. Sick Leave (SL)", quote=quote)


def test_short_quote_is_kept() -> None:
    assert make_citation("A medical certificate is required").quote == "A medical certificate is required"


def test_long_quote_is_cut_to_25_words() -> None:
    quote = " ".join(f"word{i}" for i in range(60))
    cut = make_citation(quote).quote
    assert len(cut.replace(" ...", "").split()) == 25
    assert cut.endswith("...")


def test_answer_without_citations_must_escalate() -> None:
    answer = PolicyAnswer(answer="Not found.", citations=[], confidence="low", escalate_to_hr=False)
    assert answer.escalate_to_hr is True


def test_answer_with_citation_keeps_its_flag() -> None:
    answer = PolicyAnswer(answer="No.", citations=[make_citation()], confidence="high",
                          escalate_to_hr=False)
    assert answer.escalate_to_hr is False


def test_bad_confidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PolicyAnswer(answer="x", citations=[], confidence="sure", escalate_to_hr=True)


def test_context_shows_source_and_section_of_every_chunk() -> None:
    docs = [
        Document(page_content="## 3. Casual Leave (CL)\n- 8 days.",
                 metadata={"source": "leave_policy.md", "section": "3. Casual Leave (CL)",
                           "policy_effective_date": "2026-04-01"}),
        Document(page_content="## 5. Security\n- Use VPN.",
                 metadata={"source": "wfh_policy.md", "section": "5. Security",
                           "policy_effective_date": "2026-01-15"}),
    ]
    text = format_context(docs)
    assert "source: leave_policy.md | section: 3. Casual Leave (CL)" in text
    assert "source: wfh_policy.md | section: 5. Security" in text


def test_prompt_has_no_stray_braces() -> None:
    """Curly braces would break the prompt template."""
    assert "{" not in SYSTEM_PROMPT and "}" not in SYSTEM_PROMPT


def test_prompt_asks_for_conditions_and_partial_answers() -> None:
    assert "condition, deadline, frequency or exception" in SYSTEM_PROMPT  # Q2, Q4, Q23 fix
    assert "whether the employee's own city is in that group" in SYSTEM_PROMPT  # Q26 fix
    assert "PART of the answer is supported" in STRICT_RULES  # Q26: strict mode must not drop to rule 5
    assert "{" not in STRICT_RULES and "}" not in STRICT_RULES