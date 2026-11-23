"""Compare the standard graph with the ReAct agent on 10 golden questions.

It USES Groq tokens (the agent calls the LLM several times per question), so it runs only a few
questions and waits between them. From the project root:
    python eval/compare_agent.py --limit 10 --sleep 5
It writes eval/agent_report.md. Add its text to eval/report.md by hand if you want it there.
"""
import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.config  # noqa: E402,F401  (loads .env)

GOLDEN_FILE = ROOT / "eval" / "golden_qa.json"
REPORT_FILE = ROOT / "eval" / "agent_report.md"
# A mix: 5 policy questions, 1 unanswerable, 1 personal, 1 policy + personal, 1 injection, 1 look-alike.
DEFAULT_IDS = [1, 3, 5, 8, 10, 12, 28, 31, 34, 40]
DEFAULT_EMPLOYEE = "E1001"


def section_number(section: str) -> str:
    """'4. Sick Leave (SL)' -> '4'."""
    match = re.match(r"\s*(\d+)\.", section)
    return match.group(1) if match else ""


def cites_expected(result: dict, source: str) -> bool:
    """True if one citation names the expected file and section number (source looks like 'leave_policy.md#4')."""
    file_name, _, number = source.partition("#")
    return any(c["source"] == file_name and section_number(c["section"]) == number for c in result["citations"])


def looks_refused(result: dict) -> bool:
    """True for a refusal: an out-of-scope reply, or no citation and a pointer to HR."""
    return result["route"] == "out_of_scope" or (not result["citations"] and result["escalate_to_hr"])


def check(question: dict, result: dict) -> bool | None:
    """A cheap automatic check. None means 'not measured here' (personal questions have no cited section).

    This is NOT the LLM judge of run_eval.py. It only asks: did an answerable question cite the right
    section, and was an unanswerable question refused?
    """
    if not question.get("answerable", True):
        return looks_refused(result)
    if question.get("type") == "personal" or not question.get("source"):
        return None
    return cites_expected(result, question["source"])


def run_mode(questions: list[dict], agent: bool, sleep: float) -> list[dict]:
    """Ask every question in one mode. A failed question (for example a rate limit) is recorded, not fatal."""
    from src import graph

    graph.set_agent_mode(agent)
    rows = []
    for number, q in enumerate(questions):
        employee = q.get("employee_id") or q.get("employee") or DEFAULT_EMPLOYEE
        row = {"id": q["id"], "ok": None, "error": ""}
        try:
            result = graph.run_query(q["question"], employee, f"cmp-{agent}-{q['id']}", log=False)
            tokens = (result["tokens"] or {}).get("total_tokens")
            row.update(route=result["route"], seconds=result["latency"]["total_seconds"], tokens=tokens,
                       tools=len(result["tools_called"]), grounded=result["grounded"], ok=check(q, result))
        except Exception as error:  # noqa: BLE001
            row.update(route="-", seconds=None, tokens=None, tools=0, grounded=False, error=type(error).__name__)
        rows.append(row)
        print(f"  {'agent   ' if agent else 'standard'} Q{q['id']}: {row['route']} "
              f"{row['seconds']} s, {row['tokens']} tokens {row['error']}")
        if number < len(questions) - 1:
            time.sleep(sleep)  # be kind to the free key
    graph.set_agent_mode(None)
    return rows


def summarize(rows: list[dict]) -> dict:
    """Averages over the questions that worked, and the automatic check score."""
    done = [r for r in rows if r["seconds"] is not None]
    checked = [r for r in done if r["ok"] is not None]
    token_rows = [r["tokens"] for r in done if r["tokens"] is not None]
    return {
        "answered": len(done), "asked": len(rows),
        "seconds": sum(r["seconds"] for r in done) / len(done) if done else 0.0,
        "tokens": sum(token_rows) / len(token_rows) if token_rows else 0.0,
        "tools": sum(r["tools"] for r in done) / len(done) if done else 0.0,
        "checked": len(checked), "passed": sum(1 for r in checked if r["ok"]),
        "grounded": sum(1 for r in done if r["grounded"]),
    }


def build_report(standard: list[dict], agent: list[dict], today: str) -> str:
    """Make the markdown text for eval/agent_report.md."""
    s, a = summarize(standard), summarize(agent)
    lines = [
        "## Optional feature: standard graph against ReAct agent", "",
        f"The same {s['asked']} golden questions were run in both modes on {today}, with a pause between "
        "questions so the free Groq key is not used up. Tokens are the total of every LLM call of a question.", "",
        "| Measure | Standard | Agent |", "|---|---|---|",
        f"| Questions answered without an error | {s['answered']}/{s['asked']} | {a['answered']}/{a['asked']} |",
        f"| Automatic check passed (right section cited, or refused when it must be) | "
        f"{s['passed']}/{s['checked']} | {a['passed']}/{a['checked']} |",
        f"| Passed the grounding check | {s['grounded']}/{s['answered']} | {a['grounded']}/{a['answered']} |",
        f"| Average time per question | {s['seconds']:.1f} s | {a['seconds']:.1f} s |",
        f"| Average tokens per question | {s['tokens']:,.0f} | {a['tokens']:,.0f} |",
        f"| Average tool calls per question | - | {a['tools']:.1f} |", "",
        "| Question | Standard route | Standard time | Standard check | Agent route | Agent time | Agent tools | Agent check |",
        "|---|---|---|---|---|---|---|---|",
    ]
    mark = {True: "pass", False: "fail", None: "n/a"}
    for x, y in zip(standard, agent):
        lines.append(f"| Q{x['id']} | {x['route']} | {_sec(x)} | {mark[x['ok']]} | {y['route']} | {_sec(y)} | "
                     f"{y['tools']} | {mark[y['ok']]} |")
    lines += ["", "How to read this: the automatic check is simpler than the LLM judge of `run_eval.py`, so "
              "these numbers are NOT the correctness score. 10 questions is a small sample. The agent makes "
              "more LLM calls per question, which costs more tokens and time and makes a free-tier rate limit "
              "more likely.", ""]
    return "\n".join(lines)


def _sec(row: dict) -> str:
    return f"{row['seconds']:.1f} s" if row["seconds"] is not None else "error"


def main() -> None:
    """Pick the questions, run both modes, save the report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=10, help="how many questions (default 10)")
    parser.add_argument("--sleep", type=float, default=5.0, help="seconds to wait between questions (default 5)")
    parser.add_argument("--ids", default="", help="comma list of golden ids, for example 1,3,28")
    args = parser.parse_args()

    ids = [int(i) for i in args.ids.split(",") if i.strip()] or DEFAULT_IDS
    golden = {q["id"]: q for q in json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))}
    questions = [golden[i] for i in ids if i in golden][: args.limit]
    print(f"Running {len(questions)} questions in standard mode, then in agent mode.")
    standard = run_mode(questions, agent=False, sleep=args.sleep)
    agent = run_mode(questions, agent=True, sleep=args.sleep)
    REPORT_FILE.write_text(build_report(standard, agent, date.today().isoformat()), encoding="utf-8")
    print(f"Saved {REPORT_FILE.name}")


if __name__ == "__main__":
    main()