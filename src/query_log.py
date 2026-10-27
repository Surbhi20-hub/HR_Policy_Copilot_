"""Per-query log (logs/queries.jsonl) and the ESTIMATED price table.

Our real cost is Rs 0 (free tiers). The prices below only show what the same tokens would
cost on a paid plan. They are rough guesses: check the provider's pricing page.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.config import ROOT_DIR

LOG_FILE = ROOT_DIR / "logs" / "queries.jsonl"  # the logs/ folder is ignored by git

# Price in USD per 1 million tokens: (input, output). ESTIMATES, not real bills.
PRICE_PER_MILLION_USD: dict[str, tuple[float, float]] = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
}
DEFAULT_PRICE = (0.075, 0.30)  # used when the model is not in the table


def mask_employee_id(employee_id: str) -> str:
    """'E1001' -> 'E1***'. Keep 2 characters so we still see the kind of employee."""
    if not employee_id:
        return ""
    return employee_id[:2] + "***"


def price_for(model: str) -> tuple[float, float]:
    """(input, output) price per 1M tokens. COST_INPUT_PER_M / COST_OUTPUT_PER_M in .env win."""
    default_in, default_out = PRICE_PER_MILLION_USD.get(model, DEFAULT_PRICE)
    return (
        float(os.getenv("COST_INPUT_PER_M", default_in)),
        float(os.getenv("COST_OUTPUT_PER_M", default_out)),
    )


def cost_from_tokens(tokens: dict | None, price_in: float, price_out: float) -> float:
    """ESTIMATED USD for one query. tokens = {'input_tokens': .., 'output_tokens': ..} or None."""
    if not tokens:
        return 0.0
    return (tokens.get("input_tokens", 0) * price_in + tokens.get("output_tokens", 0) * price_out) / 1_000_000


def estimate_cost(tokens: dict | None, model: str = "") -> float:
    """ESTIMATED USD for one query on this model."""
    price_in, price_out = price_for(model)
    return cost_from_tokens(tokens, price_in, price_out)


def append_query_log(record: dict, path: Path = LOG_FILE) -> bool:
    """Add one JSON line to the log. Returns False (and never crashes the app) if it cannot write."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False