from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import AppSettings
from app.enums import JobStatus, PaperStatus
from app.models.job import JobRecord
from app.models.paper import Paper, PaperSummary, Script
from app.providers.litellm_provider import ProviderNotReadyError
from app.providers.registry import ProviderRegistry
from app.services.analyze_script import AnalyzeScriptService
from app.services.papers import PaperRepository
from app.workers.tasks import _run_analyze_script_job


def make_scored_paper(*, source_id: str, title: str = "Scriptable paper") -> Paper:
    return Paper(
        source="arxiv",
        source_id=source_id,
        title=title,
        abstract="A concise abstract for script generation.",
        authors=["Alice", "Bob"],
        categories=["quant-ph"],
        pdf_url=f"https://arxiv.org/pdf/{source_id}",
        published_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
        raw_metadata_json={"seed": source_id},
        status=PaperStatus.SCORED,
    )


@pytest.mark.asyncio
async def test_analyze_script_service_creates_summary_script_and_marks_paper_scripted(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = make_scored_paper(source_id="2606.10001v1", title="Quantum battery breakthrough")
        session.add(paper)
        await session.commit()

        service = AnalyzeScriptService(settings, PaperRepository(), ProviderRegistry(settings))
        processed = await service.process_papers(
            session,
            limit=1,
            status=PaperStatus.SCORED,
            provider="mock",
        )

    async with session_factory() as session:
        refreshed = await session.get(Paper, paper.id)
        summary = await session.scalar(select(PaperSummary).where(PaperSummary.paper_id == paper.id))
        script = await session.scalar(select(Script).where(Script.paper_id == paper.id))

    assert processed == 1
    assert refreshed is not None
    assert refreshed.status == PaperStatus.SCRIPTED
    assert summary is not None
    assert summary.normalized_title_ru
    assert summary.normalized_abstract_ru
    assert summary.short_summary_ru
    assert summary.model_used == "mock:script-draft-v2"
    assert summary.technical_summary
    assert summary.popular_summary
    assert script is not None
    assert script.format == "short-video"
    assert script.language == "ru"
    assert isinstance(script.scene_json, dict)
    assert len(script.scene_json["scenes"]) >= 3
    assert script.model_used == "mock:script-draft-v2"


@pytest.mark.asyncio
async def test_analyze_script_service_creates_review_ready_ru_fields_for_single_paper(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        selected_paper = make_scored_paper(
            source_id="2606.10001v2",
            title="Original English title",
        )
        untouched_paper = make_scored_paper(
            source_id="2606.10001v3",
            title="Another paper",
        )
        session.add_all([selected_paper, untouched_paper])
        await session.commit()

        service = AnalyzeScriptService(settings, PaperRepository(), ProviderRegistry(settings))
        processed = await service.process_papers(
            session,
            limit=1,
            status=PaperStatus.SCORED,
            provider="mock",
            paper_id=selected_paper.id,
        )

    async with session_factory() as session:
        selected_summary = await session.scalar(
            select(PaperSummary).where(PaperSummary.paper_id == selected_paper.id)
        )
        untouched_summary = await session.scalar(
            select(PaperSummary).where(PaperSummary.paper_id == untouched_paper.id)
        )
        refreshed_selected = await session.get(Paper, selected_paper.id)
        refreshed_untouched = await session.get(Paper, untouched_paper.id)

    assert processed == 1
    assert refreshed_selected is not None
    assert refreshed_selected.status == PaperStatus.SCRIPTED
    assert selected_summary is not None
    assert selected_summary.normalized_title_ru
    assert selected_summary.normalized_abstract_ru
    assert selected_summary.short_summary_ru
    assert selected_summary.model_used == "mock:script-draft-v2"
    assert refreshed_untouched is not None
    assert refreshed_untouched.status == PaperStatus.SCORED
    assert untouched_summary is None


@pytest.mark.asyncio
async def test_analyze_script_service_enriches_mock_draft_with_litellm(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        paper = make_scored_paper(source_id="2606.10002v1")
        session.add(paper)
        await session.commit()

        registry = ProviderRegistry(settings)
        provider = registry.get_llm_provider("litellm")

        async def fake_generate(prompt: str, model: str) -> str:
            assert "popular_summary" in prompt
            assert model == settings.litellm_scoring_model
            return """
            {
              "ru_title": "RU normalized title",
              "ru_abstract": "RU normalized abstract",
              "summary": "RU short summary",
              "technical_summary": "Refined technical summary.",
              "popular_summary": "Refined popular explanation.",
              "limitations": "Refined limitations.",
              "hype_risks": "Refined hype risks.",
              "script_text": "Improved final script.",
              "scenes": [
                {"scene_number": 1, "purpose": "hook", "narration": "Scene 1", "visual_cue": "hook"},
                {"scene_number": 2, "purpose": "core", "narration": "Scene 2", "visual_cue": "diagram"},
                {"scene_number": 3, "purpose": "close", "narration": "Scene 3", "visual_cue": "takeaway"}
              ],
              "model_used": "ignored-by-service"
            }
            """

        monkeypatch.setattr(provider, "generate", fake_generate)

        service = AnalyzeScriptService(settings, PaperRepository(), registry)
        processed = await service.process_papers(
            session,
            limit=1,
            status=PaperStatus.SCORED,
            provider="litellm",
        )

    async with session_factory() as session:
        summary = await session.scalar(select(PaperSummary).where(PaperSummary.paper_id == paper.id))
        script = await session.scalar(select(Script).where(Script.paper_id == paper.id))

    assert processed == 1
    assert summary is not None
    assert summary.normalized_title_ru == "RU normalized title"
    assert summary.short_summary_ru == "RU short summary"
    assert summary.popular_summary == "Refined popular explanation."
    assert summary.model_used == "gpu/deep-analysis"
    assert script is not None
    assert script.script_text == "Improved final script."
    assert script.model_used == "gpu/deep-analysis"


@pytest.mark.asyncio
async def test_analyze_script_service_keeps_mock_result_when_litellm_enrichment_fails(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        paper = make_scored_paper(source_id="2606.10003v1")
        session.add(paper)
        await session.commit()

        registry = ProviderRegistry(settings)
        provider = registry.get_llm_provider("litellm")

        async def fake_generate(prompt: str, model: str) -> str:
            raise ProviderNotReadyError("timeout")

        monkeypatch.setattr(provider, "generate", fake_generate)

        service = AnalyzeScriptService(settings, PaperRepository(), registry)
        processed = await service.process_papers(
            session,
            limit=1,
            status=PaperStatus.SCORED,
            provider="litellm",
        )

    async with session_factory() as session:
        summary = await session.scalar(select(PaperSummary).where(PaperSummary.paper_id == paper.id))
        script = await session.scalar(select(Script).where(Script.paper_id == paper.id))

    assert processed == 1
    assert summary is not None
    assert summary.model_used == "mock:script-draft-v2"
    assert script is not None
    assert script.model_used == "mock:script-draft-v2"


@pytest.mark.asyncio
async def test_analyze_script_job_runner_marks_job_succeeded_and_persists_output(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        paper = make_scored_paper(source_id="2606.10004v1")
        job = JobRecord(
            job_type="analyze-script-papers",
            status=JobStatus.QUEUED,
            input_json={"limit": 1, "status": "scored", "provider": "mock"},
        )
        session.add_all([paper, job])
        await session.commit()

    monkeypatch.setattr("app.workers.tasks.get_settings", lambda: settings)

    await _run_analyze_script_job(job.id, {"limit": 1, "status": "scored", "provider": "mock"})

    async with session_factory() as session:
        refreshed_paper = await session.get(Paper, paper.id)
        refreshed_job = await session.get(JobRecord, job.id)

    assert refreshed_paper is not None
    assert refreshed_paper.status == PaperStatus.SCRIPTED
    assert refreshed_job is not None
    assert refreshed_job.status == JobStatus.SUCCEEDED
    assert refreshed_job.output_json == {"processed": 1}


@pytest.mark.asyncio
async def test_analyze_script_service_marks_failed_paper_and_keeps_previous_progress(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        first_paper = make_scored_paper(source_id="2606.10005v1", title="First scriptable paper")
        second_paper = make_scored_paper(source_id="2606.10006v1", title="Second scriptable paper")
        second_paper.published_at = datetime(2026, 6, 14, 9, 59, tzinfo=UTC)
        session.add_all([first_paper, second_paper])
        await session.commit()

        service = AnalyzeScriptService(settings, PaperRepository(), ProviderRegistry(settings))
        original_build = service.mock_generator.build

        def flaky_build(paper: Paper):
            if paper.source_id == "2606.10006v1":
                raise RuntimeError("synthetic mock generation failure")
            return original_build(paper)

        monkeypatch.setattr(service.mock_generator, "build", flaky_build)

        processed = await service.process_papers(
            session,
            limit=2,
            status=PaperStatus.SCORED,
            provider="mock",
        )

    async with session_factory() as session:
        refreshed_first = await session.get(Paper, first_paper.id)
        refreshed_second = await session.get(Paper, second_paper.id)

    assert processed == 1
    assert refreshed_first is not None
    assert refreshed_first.status == PaperStatus.SCRIPTED
    assert refreshed_second is not None
    assert refreshed_second.status == PaperStatus.FAILED
