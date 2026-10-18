"""Tests for src/ingest.py. They use fake embeddings, so no model download is needed."""
import json
from pathlib import Path

from langchain_core.embeddings.fake import DeterministicFakeEmbedding

from src.ingest import CHUNKS_FILENAME, POLICIES_DIR, ingest, load_policy_chunks


def test_running_ingest_twice_does_not_duplicate(tmp_path: Path) -> None:
    """The second run must add nothing and keep the same total."""
    fake = DeterministicFakeEmbedding(size=16)
    first = ingest(POLICIES_DIR, tmp_path, embeddings=fake)
    second = ingest(POLICIES_DIR, tmp_path, embeddings=fake)

    assert first.chunks_added > 0
    assert second.chunks_added == 0
    assert second.chunks_skipped == first.chunks_found
    assert second.total_in_store == first.total_in_store


def test_pdf_policy_produces_chunks(tmp_path: Path) -> None:
    """The PDF policy must give chunks with a section and a date, and reach chunks.json."""
    pdf_chunks = load_policy_chunks(POLICIES_DIR / "performance_review_policy.pdf")
    assert len(pdf_chunks) >= 6
    assert all(c.metadata["source"] == "performance_review_policy.pdf" for c in pdf_chunks)
    assert all(c.metadata["policy_effective_date"] == "2026-05-01" for c in pdf_chunks)
    sections = {c.metadata["section"] for c in pdf_chunks}
    assert "1. Scope and Review Cycle" in sections

    ingest(POLICIES_DIR, tmp_path, embeddings=DeterministicFakeEmbedding(size=16))
    rows = json.loads((tmp_path / CHUNKS_FILENAME).read_text(encoding="utf-8"))
    assert any(r["metadata"]["source"].endswith(".pdf") for r in rows)


def test_markdown_section_keeps_its_number() -> None:
    """Section text keeps its number, so citations like leave_policy.md#2 are possible."""
    chunks = load_policy_chunks(POLICIES_DIR / "leave_policy.md")
    pl = [c for c in chunks if c.metadata["section"] == "2. Earned / Privilege Leave (PL)"]
    assert len(pl) == 1
    assert pl[0].metadata["section_number"] == "2"
    assert pl[0].metadata["policy_effective_date"] == "2026-04-01"
    assert "18 days" in pl[0].page_content


def test_long_section_is_split_into_smaller_chunks(tmp_path: Path) -> None:
    """A very long section must become several chunks that all keep the same metadata."""
    long_text = " ".join(["Employees must follow the rule."] * 200)
    policy = tmp_path / "test_policy.md"
    policy.write_text(
        "---\ntitle: Test Policy\neffective_date: 2026-01-01\n---\n"
        f"# Test Policy\n\n## 1. Long Section\n{long_text}\n",
        encoding="utf-8",
    )
    chunks = load_policy_chunks(policy)
    assert len(chunks) > 1
    assert all(c.metadata["section"] == "1. Long Section" for c in chunks)