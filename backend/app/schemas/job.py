from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.enums import JobStatus, PaperStatus


class JobRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    status: PaperStatus = PaperStatus.COLLECTED
    provider: str = "mock"


class CollectJobRequest(BaseModel):
    categories: list[str] = Field(default_factory=list)
    max_results: int = Field(default=100, ge=1, le=500)


class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: JobStatus
    input_json: dict
    output_json: dict | None
    error_text: str | None
    created_at: datetime
    updated_at: datetime

