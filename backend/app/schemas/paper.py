from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import PaperStatus
from .common import PaginatedResponse


class LatestScore(BaseModel):
    final_score: float
    explanation: str
    model_used: str
    created_at: datetime


class PaperResponse(BaseModel):
    id: UUID
    source: str
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    pdf_url: str | None
    published_at: datetime
    collected_at: datetime
    status: PaperStatus
    raw_metadata_json: dict
    latest_score: LatestScore | None = None


class PaperListResponse(PaginatedResponse):
    items: list[PaperResponse]


class PaperStatusPatch(BaseModel):
    status: PaperStatus


class CollectRequest(BaseModel):
    categories: list[str] = Field(default_factory=list)
    max_results: int = Field(default=100, ge=1, le=500)


class CollectResponse(BaseModel):
    fetched: int
    inserted: int
    duplicates: int

