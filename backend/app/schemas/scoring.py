from __future__ import annotations

from pydantic import BaseModel, Field

from app.enums import PaperStatus


class ScoreBreakdown(BaseModel):
    public_interest: float = Field(ge=0, le=10)
    visual_potential: float = Field(ge=0, le=10)
    novelty: float = Field(ge=0, le=10)
    practical_relevance: float = Field(ge=0, le=10)
    mystery: float = Field(ge=0, le=10)
    credibility: float = Field(ge=0, le=10)
    explanation: str


class ScoreRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    status: PaperStatus = PaperStatus.COLLECTED
    provider: str = "mock"


class ScoreResponse(BaseModel):
    processed: int
    threshold: float
    provider: str

