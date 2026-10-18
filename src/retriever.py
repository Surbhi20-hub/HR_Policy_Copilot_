"""Three ways to find policy chunks: vector, BM25 and hybrid (both together).

Run a side-by-side demo from the project root:  python -m src.retriever
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda

try:
    from langchain.retrievers import EnsembleRetriever
except ImportError:  # newer LangChain moved it
    from langchain_classic.retrievers import EnsembleRetriever

from src.config import CHROMA_DIR, COLLECTION_NAME, ROOT_DIR, get_embeddings
from src.ingest import CHUNKS_FILENAME

TOP_K = 5
BM25_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5
GOLDEN_FILE = ROOT_DIR / "eval" / "golden_qa.json"
DEMO_QUESTION_IDS = [1, 3, 5, 8, 10, 12]  # 5 answerable questions and 1 unanswerable

# Filler words that tell BM25 nothing about the topic.
STOP_WORDS = {
    "a", "an", "the", "i", "me", "my", "do", "does", "is", "are", "can", "to", "of",
    "in", "for", "on", "and", "or", "by", "at", "how", "what", "which", "where",
    "when", "get", "we", "you", "it", "be", "from", "with",
}


@lru_cache(maxsize=1)
def _load_embeddings() -> Embeddings:
    """Load the embedding model once and reuse it (loading takes a few seconds)."""
    return get_embeddings()


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers only (so 'Leave?' matches 'leave'), minus filler words."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def load_chunks(chunks_file: Path = CHROMA_DIR / CHUNKS_FILENAME) -> list[Document]:
    """Read the chunks saved by `python -m src.ingest` as Document objects."""
    if not chunks_file.exists():
        raise FileNotFoundError(f"{chunks_file} not found. Run first: python -m src.ingest")
    rows = json.loads(chunks_file.read_text(encoding="utf-8"))
    return [Document(page_content=row["text"], metadata=row["metadata"]) for row in rows]


def get_vector_retriever(k: int = TOP_K) -> BaseRetriever:
    """Search by MEANING, using the Chroma index."""
    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=_load_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )
    if not store.get()["ids"]:
        raise RuntimeError("The Chroma index is empty. Run first: python -m src.ingest")
    return store.as_retriever(search_kwargs={"k": k})


def get_bm25_retriever(k: int = TOP_K) -> BM25Retriever:
    """Search by exact WORDS, built from the saved chunks file."""
    return BM25Retriever.from_documents(load_chunks(), preprocess_func=tokenize, k=k)


def get_hybrid_retriever(
    k: int = TOP_K,
    bm25_weight: float = BM25_WEIGHT,
    vector_weight: float = VECTOR_WEIGHT,
) -> Runnable:
    """Mix BM25 and vector results, then keep the best k."""
    ensemble = EnsembleRetriever(
        retrievers=[get_bm25_retriever(k), get_vector_retriever(k)],
        weights=[bm25_weight, vector_weight],
    )
    # The mix can hold up to 2*k chunks, so cut it back to k.
    return ensemble | RunnableLambda(lambda docs: docs[:k])


def expected_rank(docs: list[Document], expected_source: str | None) -> int | None:
    """Return the position (1, 2, ...) of the expected section, or None if it is missing."""
    if not expected_source:
        return None
    file_name, _, number = expected_source.partition("#")
    for rank, doc in enumerate(docs, start=1):
        if doc.metadata["source"] == file_name and doc.metadata["section_number"] == number:
            return rank
    return None


def print_docs(docs: list[Document], expected_source: str | None = None,
               show_text: bool = False) -> None:
    """Print each chunk as: rank. source | section  (and mark the expected one)."""
    file_name, _, number = (expected_source or "").partition("#")
    for rank, doc in enumerate(docs, start=1):
        meta = doc.metadata
        is_expected = meta["source"] == file_name and meta["section_number"] == number
        mark = "   <== expected" if is_expected else ""
        print(f"  {rank}. {meta['source']} | {meta['section']}{mark}")
        if show_text:
            body = doc.page_content.split("\n", 1)[-1].replace("\n", " ")
            print(f"       {body[:100]}...")


def load_demo_questions() -> list[dict]:
    """Pick the demo questions out of eval/golden_qa.json."""
    rows = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    return [row for row in rows if row["id"] in DEMO_QUESTION_IDS]


def main() -> None:
    """Run every demo question through all three retrievers and compare."""
    retrievers = {
        "vector": get_vector_retriever(),
        "bm25": get_bm25_retriever(),
        "hybrid": get_hybrid_retriever(),
    }
    summary: list[tuple[int, dict[str, int | None]]] = []

    for row in load_demo_questions():
        print("=" * 70)
        print(f"Q{row['id']}: {row['question']}")
        print(f"Expected source: {row['source'] or 'none (should be refused)'}")
        ranks: dict[str, int | None] = {}
        for name, retriever in retrievers.items():
            docs = retriever.invoke(row["question"])
            print(f"\n [{name}]")
            print_docs(docs, row["source"])
            ranks[name] = expected_rank(docs, row["source"])
        summary.append((row["id"], ranks))

    print("\n" + "=" * 70)
    print("Where did the expected section appear? (1 = best, - = not in top 5)")
    print(f"{'Question':<10}{'vector':<10}{'bm25':<10}{'hybrid':<10}")
    for question_id, ranks in summary:
        cells = [str(ranks[name]) if ranks[name] else "-" for name in retrievers]
        print(f"Q{question_id:<9}{cells[0]:<10}{cells[1]:<10}{cells[2]:<10}")
    print("(Q12 is unanswerable, so '-' is expected for it.)")


if __name__ == "__main__":
    main()