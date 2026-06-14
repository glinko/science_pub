from app.config import AppSettings
from app.providers.litellm_provider import LiteLLMProvider
from app.providers.mock_llm import MockLLMProvider
from app.providers.registry import ProviderRegistry


def test_provider_registry_returns_expected_llm_provider() -> None:
    settings = AppSettings(
        database_url="sqlite+aiosqlite:///science.db",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="key",
        minio_secret_key="secret",
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
        litellm_api_key="science-pub-local-only",
    )
    registry = ProviderRegistry(settings=settings)
    litellm_provider = registry.get_llm_provider("litellm")

    assert isinstance(registry.get_llm_provider("mock"), MockLLMProvider)
    assert isinstance(litellm_provider, LiteLLMProvider)
    assert litellm_provider.timeout == settings.litellm_timeout_seconds
    assert litellm_provider.api_key == "science-pub-local-only"
