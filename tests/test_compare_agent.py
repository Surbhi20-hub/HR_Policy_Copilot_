"""Tests for the pure helper functions of eval/compare_agent.py."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name: str):
    """Import a script from the eval folder (it is not a package)."""
    sys.path.insert(0, str(ROOT / "eval"))
    spec = importlib.util.spec_from_file_location(name, ROOT / "eval" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_cites_expected_and_refusal_checks() -> None:
    module = load("compare_agent")
    cited = {"route": "policy", "escalate_to_hr": False,
             "citations": [{"source": "leave_policy.md", "section": "4. Sick Leave (SL)", "quote": "q"}]}
    refused = {"route": "policy", "escalate_to_hr": True, "citations": []}
    assert module.section_number("4. Sick Leave (SL)") == "4"
    assert module.cites_expected(cited, "leave_policy.md#4") and not module.cites_expected(cited, "leave_policy.md#5")
    assert module.check({"answerable": True, "type": "policy", "source": "leave_policy.md#4"}, cited) is True
    assert module.check({"answerable": False}, refused) is True and module.check({"answerable": False}, cited) is False
    assert module.check({"answerable": True, "type": "personal", "source": None}, cited) is None


def test_agent_report_shows_both_modes() -> None:
    module = load("compare_agent")
    row = {"id": 1, "route": "policy", "seconds": 4.0, "tokens": 3000, "tools": 2, "grounded": True, "ok": True, "error": ""}
    text = module.build_report([dict(row, tools=0)], [row], "2026-11-22")
    assert "Standard" in text and "Agent" in text and "| Q1 |" in text