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
