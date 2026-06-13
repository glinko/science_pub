from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings
from app.db import get_session
from app.dependencies import get_collector, get_paper_repository, get_settings_dependency
from app.schemas.paper import CollectRequest, CollectResponse
from app.services.arxiv import ArxivCollector
from app.services.papers import PaperRepository

router = APIRouter()


@router.post("/collect/arxiv", response_model=CollectResponse)
async def collect_arxiv(
    payload: CollectRequest,
    session: AsyncSession = Depends(get_session),
    settings: AppSettings = Depends(get_settings_dependency),
    collector: ArxivCollector = Depends(get_collector),
    paper_repository: PaperRepository = Depends(get_paper_repository),
) -> CollectResponse:
    categories = payload.categories or settings.default_arxiv_categories
    papers = await collector.collect(categories=categories, max_results=payload.max_results)
    inserted, duplicates = await paper_repository.upsert_collected(session, papers)
    return CollectResponse(fetched=len(papers), inserted=inserted, duplicates=duplicates)

