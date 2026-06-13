from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .version import APP_VERSION


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SCIENCE_PUB_",
        extra="ignore",
    )

    app_name: str = "Science Pub"
    environment: str = "development"
    version: str = APP_VERSION
    testing: bool = False
    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    qdrant_url: str
    litellm_url: str
    litellm_model: str | None = None
    n8n_url: str = "http://n8n:5678"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    request_timeout_seconds: float = 10.0
    default_arxiv_categories: list[str] = Field(
        default_factory=lambda: [
            "cs.AI",
            "cs.LG",
            "quant-ph",
            "gr-qc",
            "astro-ph",
            "cond-mat",
            "hep-th",
            "physics.pop-ph",
        ]
    )
    minio_buckets: list[str] = Field(
        default_factory=lambda: ["papers", "assets", "audio", "videos", "thumbnails"]
    )
    score_threshold: float = 7.0
    provider_default: str = "mock"
    health_warning_litellm: str = "litellm_upstream_inference_not_configured"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
