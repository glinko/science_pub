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
                normalized_title_ru="\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
                normalized_abstract_ru="\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
                short_summary_ru="\u041a\u043e\u0440\u043e\u0442\u043a\u043e\u0435 summary \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440\u0430.",
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
        "ru_title": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
        "ru_abstract": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
        "summary": "\u041a\u043e\u0440\u043e\u0442\u043a\u043e\u0435 summary \u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440\u0430.",
        "model_used": "gpu/deep-analysis",
    }


@pytest.mark.asyncio
async def test_get_paper_returns_latest_complete_review_ready_draft(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.20002v1",
            title="Original title",
            abstract="Original abstract",
            authors=["Editor"],
            categories=["cs.AI"],
            pdf_url="https://example.invalid/paper.pdf",
            published_at=datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "detail-latest"},
            status=PaperStatus.SCRIPTED,
        )
        session.add(paper)
        await session.flush()
        session.add_all(
            [
                PaperSummary(
                    paper_id=paper.id,
                    normalized_title_ru="\u0421\u0442\u0430\u0440\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
                    normalized_abstract_ru="\u0421\u0442\u0430\u0440\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
                    short_summary_ru="\u0421\u0442\u0430\u0440\u043e\u0435 \u043f\u043e\u043b\u043d\u043e\u0435 summary.",
                    model_used="gpu/older-complete",
                    created_at=datetime(2026, 6, 14, 12, 5, tzinfo=UTC),
                ),
                PaperSummary(
                    paper_id=paper.id,
                    normalized_title_ru="\u041d\u043e\u0432\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
                    normalized_abstract_ru="\u041d\u043e\u0432\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
                    short_summary_ru="\u041d\u043e\u0432\u043e\u0435 \u043f\u043e\u043b\u043d\u043e\u0435 summary.",
                    model_used="gpu/newer-complete",
                    created_at=datetime(2026, 6, 14, 12, 15, tzinfo=UTC),
                ),
                PaperSummary(
                    paper_id=paper.id,
                    normalized_title_ru="\u0421\u0430\u043c\u044b\u0439 \u043d\u043e\u0432\u044b\u0439 \u043d\u0435\u043f\u043e\u043b\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
                    normalized_abstract_ru="\u0421\u0430\u043c\u044b\u0439 \u043d\u043e\u0432\u044b\u0439 \u043d\u0435\u043f\u043e\u043b\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
                    short_summary_ru=None,
                    model_used="gpu/newest-incomplete",
                    created_at=datetime(2026, 6, 14, 12, 30, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()

    response = await app_client.get(f"/papers/{paper.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_draft"] == {
        "ru_title": "\u041d\u043e\u0432\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a",
        "ru_abstract": "\u041d\u043e\u0432\u044b\u0439 \u043f\u043e\u043b\u043d\u044b\u0439 \u0430\u0431\u0441\u0442\u0440\u0430\u043a\u0442",
        "summary": "\u041d\u043e\u0432\u043e\u0435 \u043f\u043e\u043b\u043d\u043e\u0435 summary.",
        "model_used": "gpu/newer-complete",
    }
