from __future__ import annotations

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings
from app.enums import PaperStatus
from app.models.paper import Paper, PaperScore
from app.providers.litellm_provider import ProviderNotReadyError
from app.providers.registry import ProviderRegistry
from app.schemas.scoring import ScoreBreakdown

from .llm_scoring import LiteLLMPaperScorer
from .papers import PaperRepository


def compute_final_score(breakdown: ScoreBreakdown) -> float:
    final_score = (
        0.30 * breakdown.public_interest
        + 0.20 * breakdown.visual_potential
        + 0.20 * breakdown.novelty
        + 0.15 * breakdown.practical_relevance
        + 0.10 * breakdown.mystery
        + 0.05 * breakdown.credibility
    )
    return round(final_score, 2)


class MockPaperScorer:
    def score_paper(self, paper: Paper) -> ScoreBreakdown:
        digest = hashlib.sha256(f"{paper.title}|{paper.abstract}".encode("utf-8")).digest()
        values = [round(5 + (byte / 255) * 5, 2) for byte in digest[:6]]
        explanation = (
            f"Mock scoring for '{paper.title[:60]}': "
            f"interest={values[0]}, visuals={values[1]}, novelty={values[2]}."
        )
        return ScoreBreakdown(
            public_interest=values[0],
            visual_potential=values[1],
            novelty=values[2],
            practical_relevance=values[3],
            mystery=values[4],
            credibility=values[5],
            explanation=explanation,
        )


class ScoringService:
    def __init__(
        self,
        settings: AppSettings,
        paper_repository: PaperRepository,
        provider_registry: ProviderRegistry,
    ) -> None:
        self.settings = settings
        self.paper_repository = paper_repository
        self.provider_registry = provider_registry
        self.mock_scorer = MockPaperScorer()

    async def score_papers(
        self,
        session: AsyncSession,
        *,
        limit: int,
        status: PaperStatus,
        provider: str,
    ) -> int:
        papers = await self.paper_repository.fetch_for_scoring(session, limit=limit, status=status)
        processed = 0
        for paper in papers:
            try:
                breakdown, model_used = await self._score_single_paper(paper, provider)
            except ValueError:
                if provider == "litellm":
                    paper.status = PaperStatus.FAILED
                    await session.commit()
                    continue
                raise
            except ProviderNotReadyError:
                await session.commit()
                raise

            final_score = compute_final_score(breakdown)
            session.add(
                PaperScore(
                    paper_id=paper.id,
                    public_interest=breakdown.public_interest,
                    visual_potential=breakdown.visual_potential,
                    novelty=breakdown.novelty,
                    practical_relevance=breakdown.practical_relevance,
                    mystery=breakdown.mystery,
                    credibility=breakdown.credibility,
                    final_score=final_score,
                    explanation=breakdown.explanation,
                    model_used=model_used,
                )
            )
            paper.status = PaperStatus.SCORED
            await session.commit()
            processed += 1
        return processed

    async def _score_single_paper(
        self,
        paper: Paper,
        provider: str,
    ) -> tuple[ScoreBreakdown, str]:
        if provider == "mock":
            return self.mock_scorer.score_paper(paper), "mock:heuristic-v1"

        if provider == "litellm":
            llm_provider = self.provider_registry.get_llm_provider("litellm")
            scorer = LiteLLMPaperScorer(llm_provider, self.settings.litellm_scoring_model)
            breakdown = await scorer.score_paper(paper)
            return breakdown, self.settings.litellm_scoring_model

        llm_provider = self.provider_registry.get_llm_provider(provider)
        await llm_provider.generate(f"Score paper: {paper.title}")
        return self.mock_scorer.score_paper(paper), f"{provider}:deferred"
