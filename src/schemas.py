"""Pydantic models for the answers the LLM must return."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_QUOTE_WORDS = 25


class Citation(BaseModel):
    """One piece of evidence: which policy, which section, and a short exact quote."""

    source: str = Field(description="Policy file name exactly as in the context, e.g. leave_policy.md")
    section: str = Field(description="Section heading exactly as in the context, e.g. 4. Sick Leave (SL)")
    quote: str = Field(description="Short quote copied word-for-word from the context, at most 25 words")

    @field_validator("quote")
    @classmethod
    def limit_quote_length(cls, value: str) -> str:
        """Cut a quote that is longer than 25 words (a long quote must not crash the app)."""
        words = value.split()
        if len(words) <= MAX_QUOTE_WORDS:
            return " ".join(words)
        return " ".join(words[:MAX_QUOTE_WORDS]) + " ..."


class PolicyAnswer(BaseModel):
    """The full answer: text, evidence, how sure we are, and whether HR should be contacted."""

    answer: str = Field(description="Short plain-language answer based only on the policy context")
    citations: list[Citation] = Field(
        description="One citation per policy rule used. Empty list if the answer was not found."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="high = clearly stated, medium = partly stated, low = not found or unclear"
    )
    escalate_to_hr: bool = Field(
        description="True if the employee should contact HR (answer not found or not fully defined)"
    )

    @model_validator(mode="after")
    def no_citations_means_escalate(self) -> "PolicyAnswer":
        """An answer with no evidence must always send the employee to HR."""
        if not self.citations:
            self.escalate_to_hr = True
        return self