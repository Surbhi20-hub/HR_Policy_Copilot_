"""Tests for src/config.py: changing LLM_PROVIDER in .env must change the model that is built."""
import pytest

from src import config


class FakeGroqModel:
    """Stands in for ChatGroq."""


class FakeGeminiModel:
    """Stands in for ChatGoogleGenerativeAI."""


class FakeOpenAIModel:
    """Stands in for ChatOpenAI."""


FAKE_CLASSES = {"groq": FakeGroqModel, "google_genai": FakeGeminiModel, "openai": FakeOpenAIModel}


@pytest.fixture
def fake_init_chat_model(monkeypatch):
    """Replace LangChain's init_chat_model with a fake that records how it was called."""
    calls: list[dict] = []

    def fake(model: str, model_provider: str, temperature: float):
        calls.append({"model": model, "provider": model_provider, "temperature": temperature})
        return FAKE_CLASSES[model_provider]()

    monkeypatch.setattr(config, "init_chat_model", fake)
    return calls


def test_changing_the_provider_in_env_changes_the_model_class(monkeypatch, fake_init_chat_model) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-20b")
    assert type(config.get_llm()) is FakeGroqModel

    monkeypatch.setenv("LLM_PROVIDER", "google_genai")  # the only change: .env, no code
    monkeypatch.setenv("LLM_MODEL", "gemini-test")
    assert type(config.get_llm()) is FakeGeminiModel

    assert [c["provider"] for c in fake_init_chat_model] == ["groq", "google_genai"]
    assert [c["model"] for c in fake_init_chat_model] == ["openai/gpt-oss-20b", "gemini-test"]


def test_temperature_is_passed_on(monkeypatch, fake_init_chat_model) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    config.get_llm(temperature=0.3)
    assert fake_init_chat_model[0]["temperature"] == 0.3


def test_unknown_embedding_provider_gives_a_clear_error(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "nonsense")
    with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
        config.get_embeddings()