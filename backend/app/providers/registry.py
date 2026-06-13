from __future__ import annotations

from .litellm_provider import LiteLLMProvider
from .mock_llm import MockLLMProvider
from app.config import AppSettings


class ProviderRegistry:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._llm_providers = {
            "mock": MockLLMProvider(),
            "litellm": LiteLLMProvider(
                base_url=settings.litellm_url,
                timeout=settings.litellm_timeout_seconds,
                default_model=settings.litellm_model,
                api_key=settings.litellm_api_key,
            ),
        }

    def get_llm_provider(self, provider_name: str):
        try:
            return self._llm_providers[provider_name]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_name}") from exc
