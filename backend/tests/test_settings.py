from app.config import AppSettings


def test_settings_expose_default_buckets() -> None:
    settings = AppSettings(
        database_url="sqlite+aiosqlite:///science.db",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="key",
        minio_secret_key="secret",
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
    )

    assert settings.minio_buckets == ["papers", "assets", "audio", "videos", "thumbnails"]
    assert settings.default_arxiv_categories[:2] == ["cs.AI", "cs.LG"]
    assert settings.arxiv_base_url == "https://export.arxiv.org/api/query"


def test_settings_expose_gpu_integration_defaults() -> None:
    settings = AppSettings(
        database_url="sqlite+aiosqlite:///science.db",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="key",
        minio_secret_key="secret",
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
    )

    assert settings.gpu_node_host == "192.168.88.20"
    assert str(settings.gpu_llm_fast_url) == "http://192.168.88.20:9000/v1"
    assert str(settings.gpu_llm_deep_url) == "http://192.168.88.20:9000/v1"
    assert str(settings.gpu_embeddings_url) == "http://192.168.88.20:9001/v1"
    assert str(settings.gpu_tts_url) == "http://127.0.0.1:5005"
    assert settings.health_warning_gpu_partial == "gpu_integrations_declared_but_not_wired"


def test_settings_expose_litellm_scoring_defaults() -> None:
    settings = AppSettings(
        database_url="sqlite+aiosqlite:///science.db",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="key",
        minio_secret_key="secret",
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
    )

    assert settings.litellm_api_key is None
    assert settings.litellm_scoring_model == "gpu/deep-analysis"
    assert settings.litellm_timeout_seconds == 30.0
    assert settings.request_timeout_seconds == 10.0
    assert settings.provider_default == "mock"
