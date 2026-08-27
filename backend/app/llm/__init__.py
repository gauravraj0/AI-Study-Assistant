"""Factory: pick the best available provider from the environment."""

from functools import lru_cache

from ..config import settings
from .base import Embedder, LLMProvider
from .embeddings import GeminiEmbedder, LocalEmbedder, OpenAIEmbedder
from .local import LocalProvider
from .remote import GeminiProvider, OpenAIProvider


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    local = LocalProvider()
    mode = settings.llm_provider
    if mode == "auto":
        mode = "openai" if settings.openai_api_key else ("gemini" if settings.gemini_api_key else "local")
    if mode == "openai" and settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key, settings.openai_model, settings.openai_embed_model, local)
    if mode == "gemini" and settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, local)
    return local


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    local = LocalEmbedder()
    mode = settings.llm_provider
    if mode == "auto":
        mode = "openai" if settings.openai_api_key else ("gemini" if settings.gemini_api_key else "local")
    if mode == "openai" and settings.openai_api_key:
        return OpenAIEmbedder(settings.openai_api_key, settings.openai_embed_model, fallback=local)
    if mode == "gemini" and settings.gemini_api_key:
        return GeminiEmbedder(settings.gemini_api_key, fallback=local)
    return local
