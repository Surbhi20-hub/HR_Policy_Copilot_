"""Safety tests: no API key written in the code, and the .env file is ignored by Git."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKIP_FOLDERS = {".git", ".venv", "venv", "__pycache__", "chroma_db", "logs", ".pytest_cache", "node_modules"}
CHECKED_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".ini", ".yml", ".yaml", ".cfg", ".example"}

# The first letters of real keys, then a long run of key characters.
KEY_PATTERNS = {
    "Groq key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Google key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    "LangSmith key": re.compile(r"lsv2_(?:pt|sk)_[A-Za-z0-9]{20,}"),
    "HuggingFace token": re.compile(r"hf_[A-Za-z0-9]{30,}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "key assigned in code": re.compile(r"""(?i)(api_?key|secret|token)\s*[=:]\s*["'][^"'\s]{16,}["']"""),
}


def find_secrets(text: str) -> list[str]:
    """Names of the key patterns that match this text."""
    return [name for name, pattern in KEY_PATTERNS.items() if pattern.search(text)]


def project_files() -> list[Path]:
    """Every text file we could commit (the .env file is skipped on purpose: it is ignored by Git)."""
    files = []
    for path in ROOT.rglob("*"):
        parts = set(path.relative_to(ROOT).parts)
        if parts & SKIP_FOLDERS or not path.is_file() or path.name == ".env":
            continue
        if path.suffix in CHECKED_SUFFIXES or path.name.startswith(".env"):
            files.append(path)
    return files


def test_scanner_finds_fake_keys_and_ignores_normal_text() -> None:
    fake_groq = "gsk_" + "a1B2" * 8  # built at run time, so this file itself never contains a key
    fake_google = "AIza" + "x" * 35
    assert find_secrets(f"GROQ_API_KEY={fake_groq}") == ["Groq key"]
    assert find_secrets(f"key = {fake_google}") == ["Google key"]
    assert find_secrets('api_key = "' + "abcdefgh" * 3 + '"') == ["key assigned in code"]
    assert find_secrets("GROQ_API_KEY=your-key-here") == []  # a placeholder is fine
    assert find_secrets("api_key = os.getenv('GROQ_API_KEY')") == []


def test_no_hard_coded_keys_in_the_project() -> None:
    problems = []
    for path in project_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        problems += [f"{path.relative_to(ROOT)}: {name}" for name in find_secrets(text)]
    assert problems == [], "Remove these keys and put them in .env: " + "; ".join(problems)


def gitignore_lines() -> set[str]:
    gitignore = ROOT / ".gitignore"
    assert gitignore.exists(), ".gitignore is missing"
    return {line.strip().rstrip("/") for line in gitignore.read_text(encoding="utf-8").splitlines()}


def test_gitignore_lists_env_and_the_private_folders() -> None:
    lines = gitignore_lines()
    for needed in (".env", "logs", "chroma_db"):
        assert needed in lines, f"add '{needed}' to .gitignore"


def test_git_really_ignores_the_env_file_and_does_not_track_it() -> None:
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("git is not available or this is not a Git folder")
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert ignored.returncode == 0, ".env is NOT ignored by Git"
    tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True)
    assert tracked.stdout.strip() == "", ".env is already tracked by Git: run 'git rm --cached .env'"