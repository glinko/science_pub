from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import PaperStatus
from app.models.paper import Paper, PaperScore, PaperSummary, Script
from app.schemas.paper import LatestScore, PaperDetailResponse, PaperResponse
from app.schemas.review_ready import ReviewDraftResponse

from .arxiv import CollectedPaper

if TYPE_CHECKING:
    from app.schemas.analyze_script import AnalyzeScriptDraft


class PaperRepository:
    async def upsert_collected(
        self,
        session: AsyncSession,
        collected_papers: list[CollectedPaper],
    ) -> tuple[int, int]:
        inserted = 0
        duplicates = 0
        for collected in collected_papers:
            existing = await session.scalar(
                select(Paper).where(
                    Paper.source == collected.source,
                    Paper.source_id == collected.source_id,
                )
            )
            if existing is not None:
                duplicates += 1
                continue
            session.add(
                Paper(
                    source=collected.source,
                    source_id=collected.source_id,
                    title=collected.title,
                    abstract=collected.abstract,
                    authors=collected.authors,
                    categories=collected.categories,
                    pdf_url=collected.pdf_url,
                    published_at=collected.published_at,
                    raw_metadata_json=collected.raw_metadata_json,
                )
            )
            inserted += 1
        await session.commit()
        return inserted, duplicates

    async def list_papers(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
        source: str | None,
        category: str | None,
        published_from,
        published_to,
        status: PaperStatus | None,
        min_score: float | None,
        include_scores: bool,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[int, list[PaperResponse]]:
        statement: Select[tuple[Paper]] = select(Paper)
        count_statement = select(func.count(Paper.id))
        conditions = []
        if source:
            conditions.append(Paper.source == source)
        if category:
            conditions.append(Paper.categories.contains([category]))
        if published_from:
            conditions.append(Paper.published_at >= published_from)
        if published_to:
            conditions.append(Paper.published_at <= published_to)
        if status:
            conditions.append(Paper.status == status)
        if min_score is not None:
            paper_ids = select(PaperScore.paper_id).where(PaperScore.final_score >= min_score)
            conditions.append(Paper.id.in_(paper_ids))
        if search and search.strip():
            needle = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(Paper.title).like(needle),
                    func.lower(Paper.source_id).like(needle),
                )
            )
        for condition in conditions:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)

        sort_column = {
            "published_at": Paper.published_at,
            "collected_at": Paper.collected_at,
            "title": Paper.title,
        }.get(sort_by, Paper.published_at)
        statement = statement.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
        statement = statement.offset(offset).limit(limit)

        total = int((await session.scalar(count_statement)) or 0)
        papers = list((await session.scalars(statement)).all())
        score_map = await self._latest_scores_map(session, [paper.id for paper in papers]) if include_scores else {}
        return total, [self._to_response(paper, score_map.get(paper.id)) for paper in papers]

    async def get_paper(
        self,
        session: AsyncSession,
        paper_id: UUID,
        *,
        include_score: bool = True,
    ) -> PaperDetailResponse | None:
        statement = select(Paper).options(selectinload(Paper.summaries)).where(Paper.id == paper_id)
        paper = await session.scalar(statement)
        if paper is None:
            return None
        score = None
        if include_score:
            score = (await self._latest_scores_map(session, [paper.id])).get(paper.id)
        return self._to_detail_response(paper, score)

    async def update_status(
        self,
        session: AsyncSession,
        paper_id: UUID,
        status: PaperStatus,
    ) -> Paper | None:
        paper = await session.get(Paper, paper_id)
        if paper is None:
            return None
        paper.status = status
        await session.commit()
        await session.refresh(paper)
        return paper

    async def fetch_for_scoring(
        self,
        session: AsyncSession,
        *,
        limit: int,
        status: PaperStatus,
    ) -> list[Paper]:
        statement = (
            select(Paper)
            .where(Paper.status == status)
            .order_by(Paper.published_at.desc())
            .limit(limit)
        )
        return list((await session.scalars(statement)).all())

    async def fetch_for_scripting(
        self,
        session: AsyncSession,
        *,
        limit: int,
        status: PaperStatus,
    ) -> list[Paper]:
        statement = (
            select(Paper)
            .where(Paper.status == status)
            .order_by(Paper.published_at.desc())
            .limit(limit)
        )
        return list((await session.scalars(statement)).all())

    async def save_generated_content(
        self,
        session: AsyncSession,
        *,
        paper: Paper,
        draft: "AnalyzeScriptDraft",
    ) -> None:
        session.add(
            PaperSummary(
                paper_id=paper.id,
                technical_summary=draft.technical_summary,
                popular_summary=draft.popular_summary,
                limitations=draft.limitations,
                hype_risks=draft.hype_risks,
                model_used=draft.model_used,
            )
        )
        session.add(
            Script(
                paper_id=paper.id,
                format="short-video",
                language="ru",
                script_text=draft.script_text,
                scene_json={"scenes": [scene.model_dump() for scene in draft.scenes]},
                model_used=draft.model_used,
            )
        )
        paper.status = PaperStatus.SCRIPTED
        await session.commit()

    async def _latest_scores_map(
        self,
        session: AsyncSession,
        paper_ids: list[UUID],
    ) -> dict[UUID, LatestScore]:
        if not paper_ids:
            return {}
        statement = (
            select(PaperScore)
            .where(PaperScore.paper_id.in_(paper_ids))
            .order_by(PaperScore.paper_id, PaperScore.created_at.desc())
        )
        scores = list((await session.scalars(statement)).all())
        latest: dict[UUID, LatestScore] = {}
        for score in scores:
            if score.paper_id not in latest:
                latest[score.paper_id] = LatestScore(
                    final_score=score.final_score,
                    explanation=score.explanation,
                    model_used=score.model_used,
                    created_at=score.created_at,
                )
        return latest

    def _to_response(self, paper: Paper, latest_score: LatestScore | None) -> PaperResponse:
        return PaperResponse(**self._response_payload(paper, latest_score))

    def _to_detail_response(
        self,
        paper: Paper,
        latest_score: LatestScore | None,
    ) -> PaperDetailResponse:
        return PaperDetailResponse(
            **self._response_payload(paper, latest_score),
            review_draft=self._latest_review_draft(paper),
        )

    def _response_payload(self, paper: Paper, latest_score: LatestScore | None) -> dict[str, object]:
        return {
            "id": cast(UUID, paper.id),
            "source": paper.source,
            "source_id": paper.source_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "authors": list(paper.authors or []),
            "categories": list(paper.categories or []),
            "pdf_url": paper.pdf_url,
            "published_at": paper.published_at,
            "collected_at": paper.collected_at,
            "status": paper.status,
            "raw_metadata_json": dict(paper.raw_metadata_json or {}),
            "latest_score": latest_score,
        }

    def _latest_review_draft(self, paper: Paper) -> ReviewDraftResponse | None:
        summaries = sorted(paper.summaries, key=lambda item: item.created_at, reverse=True)
        summary = next(
            (
                item
                for item in summaries
                if item.normalized_title_ru and item.normalized_abstract_ru and item.short_summary_ru
            ),
            None,
        )
        if summary is None:
            return None
        return ReviewDraftResponse(
            ru_title=summary.normalized_title_ru,
            ru_abstract=summary.normalized_abstract_ru,
            summary=summary.short_summary_ru,
            model_used=summary.model_used,
        )
