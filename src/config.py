"""Central config: every model is created here so the provider is switchable via .env."""
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Return the chat model chosen by LLM_PROVIDER and LLM_MODEL in .env."""
    return init_chat_model(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        model_provider=os.getenv("LLM_PROVIDER", "openai"),
        temperature=temperature,
    )


def get_embeddings() -> Embeddings:
    """Return the embedding model chosen by EMBEDDING_PROVIDER and EMBEDDING_MODEL in .env."""
    provider = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
    model = os.getenv("EMBEDDING_MODEL", "").strip() or DEFAULT_EMBEDDING_MODEL

    # Each import is inside its own branch, so we only load what we use.
    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=model,
            encode_kwargs={"normalize_embeddings": True},
        )
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model)
    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=model)

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. "
        "Use one of: huggingface, openai, ollama."
    )