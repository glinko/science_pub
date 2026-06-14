from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.enums import PaperStatus
from app.models.paper import Paper, PaperSummary


@pytest.mark.asyncio
async def test_get_paper_returns_review_ready_draft_when_available(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.20001v1",
            title="Original title",
            abstract="Original abstract",
            authors=["Editor"],
            categories=["cs.AI"],
            pdf_url="https://example.invalid/paper.pdf",
            published_at=datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "detail"},
            status=PaperStatus.SCRIPTED,
        )
        session.add(paper)
        await session.flush()
        session.add(
            PaperSummary(
                paper_id=paper.id,
                normalized_title_ru="Нормализованный заголовок",
                normalized_abstract_ru="Нормализованный абстракт",
                short_summary_ru="Короткое summary для редактора.",
                technical_summary="Tech summary",
                popular_summary="Popular summary",
                limitations="Limitations",
                hype_risks="Hype risks",
                model_used="gpu/deep-analysis",
            )
        )
        await session.commit()

    response = await app_client.get(f"/papers/{paper.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_draft"] == {
        "ru_title": "Нормализованный заголовок",
        "ru_abstract": "Нормализованный абстракт",
        "summary": "Короткое summary для редактора.",
        "model_used": "gpu/deep-analysis",
    }
