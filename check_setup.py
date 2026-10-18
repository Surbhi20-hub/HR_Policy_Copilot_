"""Setup checker: run `python check_setup.py` from the project root.

It prints OK or FAIL (with a clear fix) for each part of the setup.
It never prints your secret keys.
"""
import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Import name of every package we need (pip name can be different).
PACKAGES: list[str] = [
    "langchain",
    "langchain_community",
    "langgraph",
    "langchain_openai",
    "langchain_google_genai",
    "langchain_groq",
    "langchain_ollama",
    "langchain_huggingface",
    "langchain_chroma",
    "chromadb",
    "rank_bm25",
    "pypdf",
    "pydantic",
    "dotenv",
    "streamlit",
    "ragas",
    "langsmith",
    "pytest",
    "reportlab",
    "sentence_transformers",
]

# Which key each provider needs.
PROVIDER_KEYS: dict[str, str] = {
    "groq": "GROQ_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
}


def show(ok: bool, name: str, message: str) -> bool:
    """Print one result line and return whether it passed."""
    print(f"[{'OK' if ok else 'FAIL'}] {name}: {message}")
    return ok


def check_python() -> bool:
    """Python must be 3.10 or newer."""
    v = sys.version_info
    ok = v >= (3, 10)
    msg = f"Python {v.major}.{v.minor}.{v.micro}"
    if not ok:
        msg += " is too old. Install Python 3.10+ from python.org."
    return show(ok, "Python version", msg)


def check_env_file() -> bool:
    """The .env file must exist in the project root."""
    ok = (ROOT / ".env").exists()
    msg = ".env found" if ok else "no .env file. Copy .env.example to .env and fill it."
    return show(ok, ".env file", msg)


def check_keys() -> bool:
    """The key for the chosen provider, and the LangSmith key, must be filled."""
    load_dotenv(ROOT / ".env")
    provider = os.getenv("LLM_PROVIDER", "").strip()
    all_ok = True

    needed = PROVIDER_KEYS.get(provider)
    if needed is None:
        all_ok = show(False, "LLM_PROVIDER", f"'{provider}' is not groq or google_genai")
    else:
        filled = bool(os.getenv(needed, "").strip())
        msg = f"{needed} is set" if filled else f"{needed} is empty in .env"
        all_ok = show(filled, "LLM key", msg) and all_ok

    ls_filled = bool(os.getenv("LANGSMITH_API_KEY", "").strip())
    ls_msg = "LANGSMITH_API_KEY is set" if ls_filled else "LANGSMITH_API_KEY is empty in .env"
    all_ok = show(ls_filled, "LangSmith key", ls_msg) and all_ok
    return all_ok


def check_packages() -> bool:
    """Every package must import. Also checks the hybrid-search class."""
    missing: list[str] = []
    for name in PACKAGES:
        try:
            importlib.import_module(name)
        except Exception as err:  # not only ImportError: some packages fail on load
            missing.append(f"{name} ({type(err).__name__})")
    ok = not missing
    msg = "all packages import" if ok else "cannot import: " + ", ".join(missing) + \
        ". Run: pip install -r requirements.txt"
    all_ok = show(ok, "Packages", msg)

    # EnsembleRetriever lives in different places in different LangChain versions.
    found = False
    for module in ("langchain.retrievers", "langchain_classic.retrievers"):
        try:
            getattr(importlib.import_module(module), "EnsembleRetriever")
            found = True
            break
        except Exception:
            continue
    msg = "EnsembleRetriever found" if found else \
        "EnsembleRetriever not found. Paste this message to your helper."
    return show(found, "Hybrid search class", msg) and all_ok


def check_llm() -> bool:
    """Make one small call to the LLM from src/config.py."""
    try:
        from src.config import get_llm

        reply = get_llm().invoke("Say hello in one short sentence.")
        text = str(reply.content).strip()
        return show(True, "LLM call", f"model said: {text}")
    except Exception as err:
        return show(False, "LLM call", f"{type(err).__name__}: {err}")


def main() -> None:
    """Run every check. Skip the LLM call if an earlier step failed."""
    print("Checking your setup...\n")
    results = [check_python(), check_env_file()]
    keys_ok = check_keys()
    packages_ok = check_packages()
    results += [keys_ok, packages_ok]

    if keys_ok and packages_ok:
        results.append(check_llm())
    else:
        print("[SKIP] LLM call: fix the FAIL lines above first.")
        results.append(False)

    print()
    if all(results):
        print("ALL GOOD! Your setup is ready.")
    else:
        print("Some checks failed. Fix the FAIL lines and run again.")
        sys.exit(1)


if __name__ == "__main__":
    main()