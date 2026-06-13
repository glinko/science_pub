from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import AppSettings
from app.enums import PaperStatus
from app.models.paper import Paper, PaperScore
from app.providers.registry import ProviderRegistry
from app.schemas.scoring import ScoreBreakdown
from app.services.papers import PaperRepository
from app.services.scoring import compute_final_score
from app.services.scoring import ScoringService


def test_compute_final_score_uses_fixed_weights() -> None:
    breakdown = ScoreBreakdown(
        public_interest=8.0,
        visual_potential=7.0,
        novelty=6.0,
        practical_relevance=5.0,
        mystery=7.0,
        credibility=6.0,
        explanation="placeholder",
    )

    assert compute_final_score(breakdown) == 6.75


@pytest.mark.asyncio
async def test_scoring_service_accepts_string_status_from_queue_payload(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.00001v1",
            title="Queue scoring test paper",
            abstract="A paper inserted to validate queued scoring.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00001v1",
            published_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "test"},
            status=PaperStatus.COLLECTED,
        )
        session.add(paper)
        await session.commit()

        service = ScoringService(settings, PaperRepository(), ProviderRegistry(settings))
        processed = await service.score_papers(
            session,
            limit=1,
            status="collected",  # type: ignore[arg-type]
            provider="mock",
        )

        await session.refresh(paper)
        scores = list((await session.scalars(select(PaperScore).where(PaperScore.paper_id == paper.id))).all())

    assert processed == 1
    assert paper.status == PaperStatus.SCORED
    assert len(scores) == 1
