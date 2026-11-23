"""Shared test setup: whatever is written in .env, the tests start in the normal (Standard) mode."""
import pytest


@pytest.fixture(autouse=True)
def default_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Standard mode, so an AGENT_MODE line in .env cannot change a test."""
    monkeypatch.setenv("AGENT_MODE", "false")