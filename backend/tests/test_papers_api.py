from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.paper import Paper, PaperSummary


@pytest.mark.asyncio
async def test_list_papers_supports_search_by_title_and_source_id(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Paper(
                    source="arxiv",
                    source_id="2606.11111v1",
                    title="Quantum relay for clean energy forecasting",
                    abstract="match by title",
                    authors=["A. One"],
                    categories=["cs.AI"],
                    pdf_url="https://example.org/1.pdf",
                    published_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
                    raw_metadata_json={},
                ),
                Paper(
                    source="arxiv",
                    source_id="2606.22222v1",
                    title="Biology paper without the keyword",
                    abstract="match by source id",
                    authors=["B. Two"],
                    categories=["q-bio"],
                    pdf_url="https://example.org/2.pdf",
                    published_at=datetime(2026, 6, 14, 11, 0, tzinfo=UTC),
                    raw_metadata_json={},
                ),
            ]
        )
        await session.commit()

    title_response = await app_client.get("/papers", params={"search": "energy"})
    source_response = await app_client.get("/papers", params={"search": "2606.22222"})

    assert title_response.status_code == 200
    assert [item["source_id"] for item in title_response.json()["items"]] == ["2606.11111v1"]
    assert source_response.status_code == 200
    assert [item["title"] for item in source_response.json()["items"]] == [
        "Biology paper without the keyword"
    ]


@pytest.mark.asyncio
async def test_patch_paper_status_accepts_approved_and_rejected(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.33333v1",
            title="Review target paper",
            abstract="status change target",
            authors=["C. Three"],
            categories=["cs.AI"],
            pdf_url="https://example.org/3.pdf",
            published_at=datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
            raw_metadata_json={},
        )
        session.add(paper)
        await session.commit()
        await session.refresh(paper)
        paper_id = str(paper.id)

    approved = await app_client.patch(f"/papers/{paper_id}/status", json={"status": "approved"})
    rejected = await app_client.patch(f"/papers/{paper_id}/status", json={"status": "rejected"})

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_list_and_patch_do_not_expose_review_draft_contract(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.44444v1",
            title="Review ready paper",
            abstract="has generated review draft",
            authors=["D. Four"],
            categories=["cs.AI"],
            pdf_url="https://example.org/4.pdf",
            published_at=datetime(2026, 6, 14, 13, 0, tzinfo=UTC),
            raw_metadata_json={},
        )
        session.add(paper)
        await session.flush()
        session.add(
            PaperSummary(
                paper_id=paper.id,
                normalized_title_ru="\u0413\u043e\u0442\u043e\u0432\u044b\u0439 RU title",
                normalized_abstract_ru="\u0413\u043e\u0442\u043e\u0432\u044b\u0439 RU abstract",
                short_summary_ru="\u0413\u043e\u0442\u043e\u0432\u043e\u0435 RU summary.",
                model_used="gpu/detail-only",
            )
        )
        await session.commit()
        await session.refresh(paper)
        paper_id = str(paper.id)

    list_response = await app_client.get("/papers")
    patch_response = await app_client.patch(f"/papers/{paper_id}/status", json={"status": "selected"})

    assert list_response.status_code == 200
    payload = list_response.json()
    listed_paper = next(item for item in payload["items"] if item["source_id"] == "2606.44444v1")
    assert "review_draft" not in listed_paper

    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "selected"
    assert "review_draft" not in patch_response.json()
