from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.router import api_router
from .config import AppSettings, get_settings
from .db import build_session_manager
from .providers.litellm_provider import LiteLLMProvider
from .providers.registry import ProviderRegistry
from .services.arxiv import ArxivCollector
from .services.health import HealthService
from .services.jobs import JobRepository
from .services.papers import PaperRepository
from .services.scoring import ScoringService
from .services.storage import StorageService
from .workers.queue import build_dispatcher


def build_storage_service(settings: AppSettings) -> StorageService:
    return StorageService(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        buckets=settings.minio_buckets,
    )


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    session_manager = build_session_manager(settings)
    provider_registry = ProviderRegistry(settings)
    storage_service = build_storage_service(settings)
    paper_repository = PaperRepository()
    job_repository = JobRepository()
    scoring_service = ScoringService(settings, paper_repository, provider_registry)
    litellm_provider = provider_registry.get_llm_provider("litellm")
    assert isinstance(litellm_provider, LiteLLMProvider)
    health_service = HealthService(settings, session_manager, storage_service, litellm_provider)
    arxiv_collector = ArxivCollector(settings.arxiv_base_url, settings.request_timeout_seconds)
    dispatcher = build_dispatcher(settings)

    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    app.state.settings = settings
    app.state.session_manager = session_manager
    app.state.provider_registry = provider_registry
    app.state.storage_service = storage_service
    app.state.paper_repository = paper_repository
    app.state.job_repository = job_repository
    app.state.scoring_service = scoring_service
    app.state.health_service = health_service
    app.state.arxiv_collector = arxiv_collector
    app.state.dispatcher = dispatcher
    app.include_router(api_router)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.session_manager.dispose()
