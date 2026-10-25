"""Small helpers for the Streamlit app. There is no Streamlit code here, so they are easy to test."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from src.config import ROOT_DIR  # importing config also loads the .env file

HRMS_FILE = ROOT_DIR / "data" / "hrms_mock.json"
FEEDBACK_FILE = ROOT_DIR / "feedback.jsonl"  # ignored by git

Rating = Literal["up", "down"]


def load_users(path: Path = HRMS_FILE) -> dict[str, str]:
    """Read the mock HR system and return {employee_id: name}."""
    records = json.loads(path.read_text(encoding="utf-8"))
    return {employee_id: record["name"] for employee_id, record in records.items()}


def user_label(employee_id: str, users: dict[str, str]) -> str:
    """Text for the dropdown, for example 'E1001 - Asha Patil'."""
    return f"{employee_id} - {users[employee_id]}"


def llm_label() -> str:
    """The provider and model chosen in .env (same defaults as src/config.py)."""
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    return f"{provider} / {model}"


def new_thread_id() -> str:
    """A new chat id. A new id means a new, empty conversation memory."""
    return f"chat-{uuid.uuid4().hex[:8]}"


def append_feedback(
    question: str,
    answer: str,
    rating: Rating,
    route: str,
    path: Path = FEEDBACK_FILE,
) -> dict:
    """Add one line (one JSON object) to feedback.jsonl and return it."""
    if rating not in ("up", "down"):
        raise ValueError(f"rating must be 'up' or 'down', not {rating!r}")
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "rating": rating,
        "route": route,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row