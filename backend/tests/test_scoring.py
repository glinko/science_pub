from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import AppSettings
from app.enums import PaperStatus
from app.models.paper import Paper, PaperScore
from app.providers.litellm_provider import ProviderNotReadyError
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


@pytest.mark.asyncio
async def test_scoring_service_uses_real_litellm_breakdown(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.00002v1",
            title="LiteLLM scoring paper",
            abstract="A paper inserted to validate the real LiteLLM scoring path.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00002v1",
            published_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "litellm-test"},
            status=PaperStatus.COLLECTED,
        )
        session.add(paper)
        await session.commit()

        registry = ProviderRegistry(settings)
        litellm_provider = registry.get_llm_provider("litellm")

        async def fake_generate(prompt: str, model: str) -> str:
            assert "LiteLLM scoring paper" in prompt
            assert model == settings.litellm_scoring_model
            return """
            {
              "public_interest": 8.0,
              "visual_potential": 7.5,
              "novelty": 9.0,
              "practical_relevance": 6.5,
              "mystery": 5.5,
              "credibility": 8.5,
              "explanation": "Strong visual story with credible results."
            }
            """

        monkeypatch.setattr(litellm_provider, "generate", fake_generate)

        service = ScoringService(settings, PaperRepository(), registry)
        processed = await service.score_papers(
            session,
            limit=1,
            status=PaperStatus.COLLECTED,
            provider="litellm",
        )

        await session.refresh(paper)
        score = await session.scalar(select(PaperScore).where(PaperScore.paper_id == paper.id))

    assert processed == 1
    assert paper.status == PaperStatus.SCORED
    assert score is not None
    assert score.public_interest == 8.0
    assert score.visual_potential == 7.5
    assert score.novelty == 9.0
    assert score.practical_relevance == 6.5
    assert score.mystery == 5.5
    assert score.credibility == 8.5
    assert score.explanation == "Strong visual story with credible results."
    assert score.final_score == 7.65
    assert score.model_used == settings.litellm_scoring_model


@pytest.mark.asyncio
async def test_scoring_service_marks_invalid_litellm_response_as_failed_and_continues(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        valid_paper = Paper(
            source="arxiv",
            source_id="2606.00003v1",
            title="Valid LiteLLM scoring paper",
            abstract="A paper that should still be scored successfully.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00003v1",
            published_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "valid"},
            status=PaperStatus.COLLECTED,
        )
        invalid_paper = Paper(
            source="arxiv",
            source_id="2606.00004v1",
            title="Invalid LiteLLM scoring paper",
            abstract="A paper that will receive malformed JSON from the model.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00004v1",
            published_at=datetime(2026, 6, 13, 12, 59, tzinfo=UTC),
            raw_metadata_json={"seed": "invalid"},
            status=PaperStatus.COLLECTED,
        )
        session.add_all([valid_paper, invalid_paper])
        await session.commit()

        registry = ProviderRegistry(settings)
        litellm_provider = registry.get_llm_provider("litellm")

        async def fake_generate(prompt: str, model: str) -> str:
            if "Invalid LiteLLM scoring paper" in prompt:
                return "not-json"
            return """
            {
              "public_interest": 8.0,
              "visual_potential": 7.5,
              "novelty": 9.0,
              "practical_relevance": 6.5,
              "mystery": 5.5,
              "credibility": 8.5,
              "explanation": "Strong visual story with credible results."
            }
            """

        monkeypatch.setattr(litellm_provider, "generate", fake_generate)

        service = ScoringService(settings, PaperRepository(), registry)
        processed = await service.score_papers(
            session,
            limit=2,
            status=PaperStatus.COLLECTED,
            provider="litellm",
        )

    async with session_factory() as session:
        refreshed_valid = await session.get(Paper, valid_paper.id)
        refreshed_invalid = await session.get(Paper, invalid_paper.id)
        valid_score = await session.scalar(select(PaperScore).where(PaperScore.paper_id == valid_paper.id))
        invalid_score = await session.scalar(select(PaperScore).where(PaperScore.paper_id == invalid_paper.id))

    assert processed == 1
    assert refreshed_valid is not None
    assert refreshed_invalid is not None
    assert refreshed_valid.status == PaperStatus.SCORED
    assert refreshed_invalid.status == PaperStatus.FAILED
    assert valid_score is not None
    assert invalid_score is None


@pytest.mark.asyncio
async def test_scoring_service_preserves_completed_scores_before_litellm_provider_failure(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with session_factory() as session:
        first_paper = Paper(
            source="arxiv",
            source_id="2606.00005v1",
            title="First LiteLLM scoring paper",
            abstract="A paper that should be scored before the provider fails.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00005v1",
            published_at=datetime(2026, 6, 13, 14, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "first"},
            status=PaperStatus.COLLECTED,
        )
        second_paper = Paper(
            source="arxiv",
            source_id="2606.00006v1",
            title="Second LiteLLM scoring paper",
            abstract="A paper that triggers a provider outage mid-batch.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00006v1",
            published_at=datetime(2026, 6, 13, 13, 59, tzinfo=UTC),
            raw_metadata_json={"seed": "second"},
            status=PaperStatus.COLLECTED,
        )
        session.add_all([first_paper, second_paper])
        await session.commit()

        registry = ProviderRegistry(settings)
        litellm_provider = registry.get_llm_provider("litellm")

        async def fake_generate(prompt: str, model: str) -> str:
            if "Second LiteLLM scoring paper" in prompt:
                raise ProviderNotReadyError("LiteLLM request failed: timeout")
            return """
            {
              "public_interest": 7.5,
              "visual_potential": 7.0,
              "novelty": 8.5,
              "practical_relevance": 6.0,
              "mystery": 5.5,
              "credibility": 8.0,
              "explanation": "The first paper was scored before the outage."
            }
            """

        monkeypatch.setattr(litellm_provider, "generate", fake_generate)

        service = ScoringService(settings, PaperRepository(), registry)
        with pytest.raises(ProviderNotReadyError, match="timeout"):
            await service.score_papers(
                session,
                limit=2,
                status=PaperStatus.COLLECTED,
                provider="litellm",
            )

    async with session_factory() as session:
        refreshed_first = await session.get(Paper, first_paper.id)
        refreshed_second = await session.get(Paper, second_paper.id)
        first_score = await session.scalar(select(PaperScore).where(PaperScore.paper_id == first_paper.id))
        second_score = await session.scalar(select(PaperScore).where(PaperScore.paper_id == second_paper.id))

    assert refreshed_first is not None
    assert refreshed_second is not None
    assert refreshed_first.status == PaperStatus.SCORED
    assert refreshed_second.status == PaperStatus.COLLECTED
    assert first_score is not None
    assert second_score is None
