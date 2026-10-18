"""Ingest policies (MD + PDF) into a persistent vector store.

TODO:
- Load .md and .pdf from data/policies
- Header-aware split; keep metadata: source, section, policy_effective_date
- Deterministic chunk IDs so re-runs don't duplicate
- Persist Chroma/FAISS index + save chunks for BM25
"""

if __name__ == "__main__":
    raise NotImplementedError("Implement ingestion")
