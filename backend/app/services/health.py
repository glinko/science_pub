from __future__ import annotations

import asyncio

import httpx
from redis.asyncio import Redis

from app.config import AppSettings
from app.db import SessionManager
from app.providers.litellm_provider import LiteLLMProvider
from app.schemas.health import ConfigCheckItem, HealthResponse, ServiceHealth

from .storage import StorageService


class HealthService:
    def __init__(
        self,
        settings: AppSettings,
        session_manager: SessionManager,
        storage_service: StorageService,
        litellm_provider: LiteLLMProvider,
    ) -> None:
        self.settings = settings
        self.session_manager = session_manager
        self.storage_service = storage_service
        self.litellm_provider = litellm_provider

    async def check(self) -> HealthResponse:
        (
            (database_ok, database_detail),
            (redis_ok, redis_detail),
            (minio_ok, minio_detail),
            (qdrant_ok, qdrant_detail),
            (litellm_ok, litellm_detail),
            (gpu_llm_fast_ok, gpu_llm_fast_detail),
            (gpu_llm_deep_ok, gpu_llm_deep_detail),
            (gpu_embeddings_ok, gpu_embeddings_detail),
        ) = await asyncio.gather(
            self.session_manager.healthcheck(),
            self._check_redis(),
            self.storage_service.healthcheck(),
            self._check_http_service(f"{self.settings.qdrant_url.rstrip('/')}/collections"),
            self.litellm_provider.healthcheck(),
            self._check_openai_compatible_upstream(self.settings.gpu_llm_fast_url),
            self._check_openai_compatible_upstream(self.settings.gpu_llm_deep_url),
            self._check_openai_compatible_upstream(self.settings.gpu_embeddings_url),
        )
        services = {
            "database": ServiceHealth(ok=database_ok, detail=database_detail),
            "redis": ServiceHealth(ok=redis_ok, detail=redis_detail),
            "minio": ServiceHealth(ok=minio_ok, detail=minio_detail),
            "qdrant": ServiceHealth(ok=qdrant_ok, detail=qdrant_detail),
            "litellm": ServiceHealth(ok=litellm_ok, detail=litellm_detail),
            "gpu_llm_fast": ServiceHealth(ok=gpu_llm_fast_ok, detail=gpu_llm_fast_detail),
            "gpu_llm_deep": ServiceHealth(ok=gpu_llm_deep_ok, detail=gpu_llm_deep_detail),
            "gpu_embeddings": ServiceHealth(
                ok=gpu_embeddings_ok,
                detail=gpu_embeddings_detail,
            ),
        }
        overall = "ok" if all(service.ok for service in services.values()) else "degraded"
        return HealthResponse(status=overall, services=services)

    async def config_checks(self) -> dict[str, ConfigCheckItem]:
        (
            (litellm_ok, litellm_detail),
            (gpu_llm_fast_ok, gpu_llm_fast_detail),
            (gpu_llm_deep_ok, gpu_llm_deep_detail),
            (gpu_embeddings_ok, gpu_embeddings_detail),
        ) = await asyncio.gather(
            self.litellm_provider.healthcheck(),
            self._check_openai_compatible_upstream(self.settings.gpu_llm_fast_url),
            self._check_openai_compatible_upstream(self.settings.gpu_llm_deep_url),
            self._check_openai_compatible_upstream(self.settings.gpu_embeddings_url),
        )
        return {
            "litellm": ConfigCheckItem(ok=litellm_ok, required=True, detail=litellm_detail),
            "gpu_llm_fast": ConfigCheckItem(
                ok=gpu_llm_fast_ok,
                required=True,
                detail=gpu_llm_fast_detail,
            ),
            "gpu_llm_deep": ConfigCheckItem(
                ok=gpu_llm_deep_ok,
                required=True,
                detail=gpu_llm_deep_detail,
            ),
            "gpu_embeddings": ConfigCheckItem(
                ok=gpu_embeddings_ok,
                required=True,
                detail=gpu_embeddings_detail,
            ),
        }

    async def _check_redis(self) -> tuple[bool, str]:
        client = Redis.from_url(self.settings.redis_url, decode_responses=True)
        try:
            await client.ping()
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)
        finally:
            await client.aclose()

    async def _check_http_service(self, url: str) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
            return True, "ok"
        except Exception as exc:  # pragma: no cover - exercised in integration
            return False, str(exc)

    async def _check_openai_compatible_upstream(self, base_url: str) -> tuple[bool, str]:
        return await self._check_http_service(f"{base_url.rstrip('/')}/models")
