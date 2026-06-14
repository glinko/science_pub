from __future__ import annotations

import asyncio
from uuid import UUID

from app.config import get_settings
from app.db import build_session_manager
from app.providers.registry import ProviderRegistry
from app.services.analyze_script import AnalyzeScriptService
from app.services.arxiv import ArxivCollector
from app.services.jobs import JobRepository
from app.services.papers import PaperRepository
from app.services.scoring import ScoringService


def run_collect_arxiv_job(job_id: str, payload: dict) -> None:
    asyncio.run(_run_collect_arxiv_job(UUID(job_id), payload))


async def _run_collect_arxiv_job(job_id: UUID, payload: dict) -> None:
    settings = get_settings()
    session_manager = build_session_manager(settings)
    jobs = JobRepository()
    papers = PaperRepository()
    collector = ArxivCollector(settings.arxiv_base_url, settings.request_timeout_seconds)
    async with session_manager.factory() as session:
        await jobs.mark_running(session, job_id)
        try:
            collected = await collector.collect(
                categories=payload.get("categories") or settings.default_arxiv_categories,
                max_results=payload.get("max_results", 100),
            )
            inserted, duplicates = await papers.upsert_collected(session, collected)
            await jobs.mark_succeeded(
                session,
                job_id,
                {"fetched": len(collected), "inserted": inserted, "duplicates": duplicates},
            )
        except Exception as exc:
            await jobs.mark_failed(session, job_id, str(exc))
    await session_manager.dispose()


def run_score_papers_job(job_id: str, payload: dict) -> None:
    asyncio.run(_run_score_papers_job(UUID(job_id), payload))


async def _run_score_papers_job(job_id: UUID, payload: dict) -> None:
    settings = get_settings()
    session_manager = build_session_manager(settings)
    jobs = JobRepository()
    papers = PaperRepository()
    scorer = ScoringService(settings, papers, ProviderRegistry(settings))
    async with session_manager.factory() as session:
        await jobs.mark_running(session, job_id)
        try:
            processed = await scorer.score_papers(
                session,
                limit=payload.get("limit", 20),
                status=payload.get("status", "collected"),
                provider=payload.get("provider", settings.provider_default),
            )
            await jobs.mark_succeeded(session, job_id, {"processed": processed})
        except Exception as exc:
            await jobs.mark_failed(session, job_id, str(exc))
    await session_manager.dispose()


def run_analyze_script_job(job_id: str, payload: dict) -> None:
    asyncio.run(_run_analyze_script_job(UUID(job_id), payload))


async def _run_analyze_script_job(job_id: UUID, payload: dict) -> None:
    settings = get_settings()
    session_manager = build_session_manager(settings)
    jobs = JobRepository()
    papers = PaperRepository()
    service = AnalyzeScriptService(settings, papers, ProviderRegistry(settings))
    async with session_manager.factory() as session:
        await jobs.mark_running(session, job_id)
        try:
            paper_id = UUID(payload["paper_id"]) if payload.get("paper_id") else None
            processed = await service.process_papers(
                session,
                limit=payload.get("limit", 1),
                status=payload.get("status", "scored"),
                provider=payload.get("provider", "mock"),
                paper_id=paper_id,
            )
            output = {"processed": processed}
            if paper_id is not None:
                output["paper_id"] = str(paper_id)
            await jobs.mark_succeeded(session, job_id, output)
        except Exception as exc:
            await jobs.mark_failed(session, job_id, str(exc))
    await session_manager.dispose()
