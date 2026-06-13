from __future__ import annotations

from pydantic import BaseModel


class ServiceHealth(BaseModel):
    ok: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    services: dict[str, ServiceHealth]


class VersionResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    build: str | None = None


class ConfigCheckItem(BaseModel):
    ok: bool
    required: bool
    detail: str


class ConfigCheckResponse(BaseModel):
    valid: bool
    warnings: list[str]
    checks: dict[str, ConfigCheckItem]
    config: dict[str, str | bool | int | None]
