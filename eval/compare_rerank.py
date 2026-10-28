"""Compare hybrid search with hybrid + cross-encoder re-ranker. Needs NO LLM and no Groq tokens.

Run from the project root:  python eval/compare_rerank.py
It writes eval/rerank_report.md, which eval/run_eval.py adds to eval/report.md.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langchain_core.documents import Document  # noqa: E402

from src.retriever import (  # noqa: E402
    DEFAULT_RERANKER, TOP_K, expected_rank, get_hybrid_retriever, get_reranked_retriever,
)

GOLDEN_FILE = ROOT / "eval" / "golden_qa.json"
REPORT_FILE = ROOT / "eval" / "rerank_report.md"
Search = Callable[[str], list[Document]]


def usable_questions(golden: list[dict]) -> list[dict]:
    """Questions that have a right section to find (skips unanswerable and personal ones)."""
    return [q for q in golden if q.get("source") and q.get("answerable", True) and q.get("type") != "personal"]


def rank_of(search: Search, question: dict) -> tuple[int | None, float]:
    """Run one search. Return (rank of the right section or None, seconds taken)."""
    start = time.perf_counter()
    docs = search(question["question"])
    seconds = time.perf_counter() - start
    return expected_rank(docs, question["source"]), seconds


def hit_rate(ranks: list[int | None], top_n: int) -> float:
    """Share of questions whose right section is in the first top_n chunks."""
    return sum(1 for r in ranks if r is not None and r <= top_n) / len(ranks) if ranks else 0.0


def mean_reciprocal_rank(ranks: list[int | None]) -> float:
    """Average of 1/rank (1.0 = always first, 0 = never found). Rewards putting it near the top."""
    return sum(1 / r for r in ranks if r) / len(ranks) if ranks else 0.0


def summarize(ranks: list[int | None], seconds: list[float]) -> dict[str, float]:
    """The numbers shown in the report for one search method."""
    return {
        "hit@1": hit_rate(ranks, 1), "hit@3": hit_rate(ranks, 3), "hit@5": hit_rate(ranks, 5),
        "mrr": mean_reciprocal_rank(ranks), "ms": 1000 * sum(seconds) / len(seconds) if seconds else 0.0,
    }


def compare(questions: list[dict], before: Search, after: Search) -> dict:
    """Run both searches on every question and collect ranks, timings and per-question changes."""
    rows = []
    for q in questions:
        rank_before, sec_before = rank_of(before, q)
        rank_after, sec_after = rank_of(after, q)
        rows.append({"id": q["id"], "question": q["question"], "source": q["source"],
                     "before": rank_before, "after": rank_after, "sec_before": sec_before, "sec_after": sec_after})
    return {
        "rows": rows,
        "before": summarize([r["before"] for r in rows], [r["sec_before"] for r in rows]),
        "after": summarize([r["after"] for r in rows], [r["sec_after"] for r in rows]),
    }


def _cell(rank: int | None) -> str:
    return str(rank) if rank else "-"


def build_report(result: dict, model: str, date: str) -> str:
    """Make the markdown text for eval/rerank_report.md."""
    b, a, rows = result["before"], result["after"], result["rows"]
    lines = [
        "## Stretch feature: cross-encoder re-ranker", "",
        f"Hybrid search takes 20 candidate chunks, then the cross-encoder `{model}` re-scores every "
        f"(question, chunk) pair and keeps the best {TOP_K}. Measured on {len(rows)} questions that have a right "
        f"section to find, on {date}. No LLM was used, so this cost no Groq tokens.", "",
        "| Metric | Hybrid (before) | Hybrid + re-ranker (after) |", "|---|---|---|",
        f"| Hit-rate@1 | {b['hit@1']:.1%} | {a['hit@1']:.1%} |",
        f"| Hit-rate@3 | {b['hit@3']:.1%} | {a['hit@3']:.1%} |",
        f"| Hit-rate@5 | {b['hit@5']:.1%} | {a['hit@5']:.1%} |",
        f"| Mean reciprocal rank (1.0 is best) | {b['mrr']:.3f} | {a['mrr']:.3f} |",
        f"| Search time per question | {b['ms']:.0f} ms | {a['ms']:.0f} ms |", "",
    ]
    changed = [r for r in rows if r["before"] != r["after"]]
    lines.append(f"Position of the right section changed for {len(changed)} of {len(rows)} questions "
                 f"({sum(1 for r in changed if (r['after'] or 99) < (r['before'] or 99))} better, "
                 f"{sum(1 for r in changed if (r['after'] or 99) > (r['before'] or 99))} worse).")
    if changed:
        lines += ["", "| Question | Before | After |", "|---|---|---|"]
        lines += [f"| Q{r['id']} {r['question'][:60]} | {_cell(r['before'])} | {_cell(r['after'])} |" for r in changed]
    lines += ["", "How to read this: hit-rate@5 of hybrid was already high, so the re-ranker cannot raise it much. "
              "The useful signals are hit@1, hit@3 and MRR (is the right chunk nearer the top?) and the search time. "
              "'-' means the right section was not in the top 5. A small sample, so small "
              "differences are not proof. Whether answers get better was NOT measured here: that needs "
              "`python eval/run_eval.py --retriever rerank` (uses Groq tokens).", ""]
    return "\n".join(lines)


def main() -> None:
    """Load the golden set, compare hybrid with the re-ranked search, save the report, print a summary."""
    from datetime import date

    import src.config  # noqa: F401  (loads .env)

    golden = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    questions = usable_questions(golden)
    before, after = get_hybrid_retriever(k=TOP_K).invoke, get_reranked_retriever(k=TOP_K).invoke
    after(questions[0]["question"])  # warm-up: loads the model, so it is not counted in the timing
    result = compare(questions, before, after)
    model = os.getenv("RERANKER_MODEL", DEFAULT_RERANKER)
    REPORT_FILE.write_text(build_report(result, model, date.today().isoformat()), encoding="utf-8")
    b, a = result["before"], result["after"]
    print(f"Questions: {len(result['rows'])}")
    for key in ("hit@1", "hit@3", "hit@5", "mrr", "ms"):
        print(f"{key:<6} before {b[key]:8.3f}   after {a[key]:8.3f}")
    print(f"Saved {REPORT_FILE.name}")


if __name__ == "__main__":
    main()