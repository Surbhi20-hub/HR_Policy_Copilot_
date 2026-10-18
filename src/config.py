"""Central config: every model is created here so the provider is switchable via .env."""
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()


def get_llm(temperature: float = 0.0):
    return init_chat_model(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        model_provider=os.getenv("LLM_PROVIDER", "openai"),
        temperature=temperature,
    )


def get_embeddings():
    # TODO: return embeddings based on EMBEDDING_PROVIDER (huggingface / openai / ollama)
    raise NotImplementedError
