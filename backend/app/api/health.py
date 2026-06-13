from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import AppSettings
from app.dependencies import get_health_service, get_settings_dependency
from app.schemas.health import ConfigCheckResponse, HealthResponse, VersionResponse
from app.services.health import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(health_service: HealthService = Depends(get_health_service)) -> HealthResponse:
    return await health_service.check()


@router.get("/version", response_model=VersionResponse)
async def version(settings: AppSettings = Depends(get_settings_dependency)) -> VersionResponse:
    return VersionResponse(
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )


@router.get("/config-check", response_model=ConfigCheckResponse)
async def config_check(
    settings: AppSettings = Depends(get_settings_dependency),
    health_service: HealthService = Depends(get_health_service),
) -> ConfigCheckResponse:
    checks = await health_service.config_checks()
    return ConfigCheckResponse(
        valid=all(item.ok or not item.required for item in checks.values()),
        warnings=[
            settings.health_warning_litellm,
            settings.health_warning_gpu_partial,
        ],
        checks=checks,
        config={
            "environment": settings.environment,
            "gpu_node_host": settings.gpu_node_host,
            "minio_secure": settings.minio_secure,
            "api_port": settings.api_port,
            "litellm_model": settings.litellm_model,
        },
    )
