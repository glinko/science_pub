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
    litellm_api_key: str | None = None
    litellm_model: str | None = None
    litellm_scoring_model: str = "gpu/deep-analysis"
    litellm_timeout_seconds: float = 60.0
    gpu_node_host: str = "192.168.88.20"
    gpu_llm_fast_url: str = "http://192.168.88.20:9000/v1"
    gpu_llm_deep_url: str = "http://192.168.88.20:9000/v1"
    gpu_embeddings_url: str = "http://192.168.88.20:9001/v1"
    gpu_tts_url: str = "http://127.0.0.1:5005"
    gpu_comfyui_url: str = "http://127.0.0.1:8188"
    gpu_render_url: str = "http://127.0.0.1:3000"
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
    health_warning_gpu_partial: str = "gpu_integrations_declared_but_not_wired"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
