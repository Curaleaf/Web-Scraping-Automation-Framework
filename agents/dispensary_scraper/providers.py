"""LLM provider configuration for the dispensary scraper agent."""

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from .settings import load_settings


def get_llm_model() -> OpenAIModel:
    """Get configured LLM model from environment settings."""
    try:
        settings = load_settings()
        provider = OpenAIProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        return OpenAIModel(settings.llm_model, provider=provider)
    except Exception:
        # For testing without env vars
        import os
        os.environ.setdefault("LLM_API_KEY", "test-key")
        settings = load_settings()
        provider = OpenAIProvider(
            base_url=settings.llm_base_url or "https://api.openai.com/v1",
            api_key="test-key"
        )
        return OpenAIModel(settings.llm_model, provider=provider)