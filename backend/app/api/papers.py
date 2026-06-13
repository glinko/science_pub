from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_paper_repository
from app.enums import PaperStatus
from app.schemas.paper import PaperListResponse, PaperResponse, PaperStatusPatch
from app.services.papers import PaperRepository

router = APIRouter()


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    session: AsyncSession = Depends(get_session),
    paper_repository: PaperRepository = Depends(get_paper_repository),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    category: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    status: PaperStatus | None = None,
    min_score: float | None = None,
    include_scores: bool = False,
    sort_by: str = "published_at",
    sort_order: str = "desc",
) -> PaperListResponse:
    total, items = await paper_repository.list_papers(
        session,
        limit=limit,
        offset=offset,
        source=source,
        category=category,
        published_from=published_from,
        published_to=published_to,
        status=status,
        min_score=min_score,
        include_scores=include_scores,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaperListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: UUID,
    session: AsyncSession = Depends(get_session),
    paper_repository: PaperRepository = Depends(get_paper_repository),
) -> PaperResponse:
    paper = await paper_repository.get_paper(session, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.patch("/papers/{paper_id}/status", response_model=PaperResponse)
async def patch_paper_status(
    paper_id: UUID,
    payload: PaperStatusPatch,
    session: AsyncSession = Depends(get_session),
    paper_repository: PaperRepository = Depends(get_paper_repository),
) -> PaperResponse:
    paper = await paper_repository.update_status(session, paper_id, payload.status)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    refreshed = await paper_repository.get_paper(session, paper_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return refreshed

