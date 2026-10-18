"""Ingest HR policies (.md and .pdf) into a persistent Chroma index.

Run from the project root:  python -m src.ingest
"""
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from src.config import CHROMA_DIR, COLLECTION_NAME, ROOT_DIR, get_embeddings

POLICIES_DIR = ROOT_DIR / "data" / "policies"
CHUNKS_FILENAME = "chunks.json"

# Rule of thumb: 1 token is about 4 characters of English.
CHUNK_SIZE = 2400      # about 600 tokens
CHUNK_OVERLAP = 300    # about 75 tokens

# PDF headings look like "2. Earned / Privilege Leave (PL)" (no full stop at the end).
HEADING_RE = re.compile(r"^\d+\.\s+[A-Z][^.]*$")
DATE_RE = re.compile(r"Effective date:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
SECTION_NUMBER_RE = re.compile(r"^(\d+)\.")


@dataclass
class IngestSummary:
    """Numbers we print at the end of a run."""

    files_read: int = 0
    chunks_found: int = 0
    chunks_added: int = 0
    chunks_skipped: int = 0
    stale_removed: int = 0
    total_in_store: int = 0
    chunks_per_file: dict[str, int] = field(default_factory=dict)


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown file into its YAML header (title, effective_date) and its body."""
    lines = text.splitlines()
    meta: dict[str, str] = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body_start = i + 1
                break
            key, _, value = lines[i].partition(":")
            meta[key.strip()] = value.strip().strip("\"'")
    return meta, "\n".join(lines[body_start:])


def pdf_text_to_markdown(text: str, fallback_title: str) -> tuple[str, str, str]:
    """Rebuild markdown from PDF text. Returns (title, effective_date, markdown)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else fallback_title
    date = "unknown"
    out: list[str] = [f"# {title}"]
    last_kind = "heading"  # what the previous output line was: heading, bullet or text

    for line in lines[1:]:
        date_match = DATE_RE.search(line)
        if date_match:
            date = date_match.group(1)
        elif HEADING_RE.match(line) and len(line) <= 80:
            out.append(f"## {line}")
            last_kind = "heading"
        elif line.startswith("- "):
            out.append(line)
            last_kind = "bullet"
        elif last_kind in ("bullet", "text"):
            out[-1] += " " + line  # a wrapped line: glue it to the line before
        else:
            out.append(line)
            last_kind = "text"
    return title, date, "\n".join(out)


def split_markdown(markdown: str, source: str, title: str, date: str) -> list[Document]:
    """Split markdown by headings, then split any big section into smaller chunks."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "section")],
        strip_headers=False,  # keep the "## 2. Heading" line inside the chunk text
    )
    sections: list[Document] = []
    for piece in header_splitter.split_text(markdown):
        # Drop the "# Title" line so every chunk looks the same; keep "## " headings.
        lines = [ln.rstrip() for ln in piece.page_content.splitlines()
                 if not ln.startswith("# ")]
        text = "\n".join(lines).strip()
        has_body = any(ln.strip() and not ln.startswith("#") for ln in lines)
        if not has_body:
            continue  # nothing but headings: skip it
        section = piece.metadata.get("section") or title
        number = SECTION_NUMBER_RE.match(section)
        sections.append(Document(
            page_content=text,
            metadata={
                "source": source,
                "title": title,
                "section": section,
                "section_number": number.group(1) if number else "",
                "policy_effective_date": date,
            },
        ))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return text_splitter.split_documents(sections)


def load_policy_chunks(path: Path) -> list[Document]:
    """Load ONE policy file (.md or .pdf) and return its chunks."""
    if path.suffix.lower() == ".pdf":
        pages = PyPDFLoader(str(path)).load()
        text = "\n".join(page.page_content for page in pages)
        title, date, markdown = pdf_text_to_markdown(text, fallback_title=path.stem)
    else:
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        title = meta.get("title", path.stem)
        date = meta.get("effective_date", "unknown")
        markdown = body
    return split_markdown(markdown, source=path.name, title=title, date=date)


def make_chunk_id(chunk: Document) -> str:
    """Same text in = same ID out, so running ingest again never makes duplicates."""
    meta = chunk.metadata
    raw = "|".join([
        meta["source"],
        meta["section"],
        meta["policy_effective_date"],
        chunk.page_content,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def load_all_chunks(policies_dir: Path) -> tuple[dict[str, Document], dict[str, int]]:
    """Read every .md and .pdf file. Returns ({chunk_id: chunk}, {file name: chunk count})."""
    files = sorted(p for p in policies_dir.iterdir()
                   if p.suffix.lower() in (".md", ".pdf"))
    if not files:
        raise FileNotFoundError(f"No .md or .pdf files found in {policies_dir}")

    chunks_by_id: dict[str, Document] = {}
    per_file: dict[str, int] = {}
    for path in files:
        chunks = load_policy_chunks(path)
        per_file[path.name] = len(chunks)
        for chunk in chunks:
            chunks_by_id.setdefault(make_chunk_id(chunk), chunk)
    return chunks_by_id, per_file


def save_chunks_json(chunks_by_id: dict[str, Document], path: Path) -> None:
    """Save every chunk to a JSON file so BM25 can be built from it later."""
    rows = [
        {"id": chunk_id, "text": chunk.page_content, "metadata": chunk.metadata}
        for chunk_id, chunk in chunks_by_id.items()
    ]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def ingest(
    policies_dir: Path = POLICIES_DIR,
    chroma_dir: Path = CHROMA_DIR,
    embeddings: Embeddings | None = None,
) -> IngestSummary:
    """Read policies, store NEW chunks in Chroma, remove old ones, save chunks.json."""
    chunks_by_id, per_file = load_all_chunks(policies_dir)
    if embeddings is None:
        embeddings = get_embeddings()

    chroma_dir.mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(chroma_dir),
    )
    existing_ids = set(store.get()["ids"])
    current_ids = set(chunks_by_id)

    new_ids = [cid for cid in chunks_by_id if cid not in existing_ids]
    stale_ids = list(existing_ids - current_ids)  # chunks of a policy that was edited or removed

    if stale_ids:
        store.delete(ids=stale_ids)
    if new_ids:
        store.add_documents([chunks_by_id[cid] for cid in new_ids], ids=new_ids)

    save_chunks_json(chunks_by_id, chroma_dir / CHUNKS_FILENAME)

    return IngestSummary(
        files_read=len(per_file),
        chunks_found=len(chunks_by_id),
        chunks_added=len(new_ids),
        chunks_skipped=len(chunks_by_id) - len(new_ids),
        stale_removed=len(stale_ids),
        total_in_store=len(store.get()["ids"]),
        chunks_per_file=per_file,
    )


def main() -> None:
    """Run the ingestion and print a short summary."""
    summary = ingest()
    print("Chunks per file:")
    for name, count in summary.chunks_per_file.items():
        print(f"  {name}: {count}")
    print()
    print(f"Files read              : {summary.files_read}")
    print(f"Chunks found            : {summary.chunks_found}")
    print(f"Chunks created (new)    : {summary.chunks_added}")
    print(f"Chunks skipped (stored) : {summary.chunks_skipped}")
    print(f"Old chunks removed      : {summary.stale_removed}")
    print(f"Total chunks in Chroma  : {summary.total_in_store}")
    print(f"Chroma folder           : {CHROMA_DIR}")
    print(f"Chunks file (for BM25)  : {CHROMA_DIR / CHUNKS_FILENAME}")


if __name__ == "__main__":
    main()