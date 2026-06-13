from __future__ import annotations

from fastapi import Request

from .config import AppSettings
from .providers.registry import ProviderRegistry
from .services.arxiv import ArxivCollector
from .services.health import HealthService
from .services.jobs import JobRepository
from .services.papers import PaperRepository
from .services.scoring import ScoringService
from .services.storage import StorageService
from .workers.queue import JobDispatcher


def get_settings_dependency(request: Request) -> AppSettings:
    return request.app.state.settings


def get_paper_repository(request: Request) -> PaperRepository:
    return request.app.state.paper_repository


def get_job_repository(request: Request) -> JobRepository:
    return request.app.state.job_repository


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry


def get_collector(request: Request) -> ArxivCollector:
    return request.app.state.arxiv_collector


def get_storage_service(request: Request) -> StorageService:
    return request.app.state.storage_service


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health_service


def get_job_dispatcher(request: Request) -> JobDispatcher:
    return request.app.state.dispatcher


def get_scoring_service(request: Request) -> ScoringService:
    return request.app.state.scoring_service

