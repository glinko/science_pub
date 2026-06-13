from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings
from app.db import get_session
from app.dependencies import get_scoring_service, get_settings_dependency
from app.providers.litellm_provider import ProviderNotReadyError
from app.schemas.scoring import ScoreRequest, ScoreResponse
from app.services.scoring import ScoringService

router = APIRouter()


@router.post("/score/papers", response_model=ScoreResponse)
async def score_papers(
    payload: ScoreRequest,
    session: AsyncSession = Depends(get_session),
    settings: AppSettings = Depends(get_settings_dependency),
    scoring_service: ScoringService = Depends(get_scoring_service),
) -> ScoreResponse:
    try:
        processed = await scoring_service.score_papers(
            session,
            limit=payload.limit,
            status=payload.status,
            provider=payload.provider,
        )
    except ProviderNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ScoreResponse(processed=processed, threshold=settings.score_threshold, provider=payload.provider)

