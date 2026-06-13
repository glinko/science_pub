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
            if provider == "mock":
                breakdown = self.mock_scorer.score_paper(paper)
                model_used = "mock:heuristic-v1"
            elif provider == "litellm":
                llm_provider = self.provider_registry.get_llm_provider("litellm")
                scorer = LiteLLMPaperScorer(llm_provider, self.settings.litellm_scoring_model)
                try:
                    breakdown = await scorer.score_paper(paper)
                except ProviderNotReadyError:
                    raise
                model_used = self.settings.litellm_scoring_model
            else:
                llm_provider = self.provider_registry.get_llm_provider(provider)
                try:
                    await llm_provider.generate(f"Score paper: {paper.title}")
                except ProviderNotReadyError:
                    raise
                breakdown = self.mock_scorer.score_paper(paper)
                model_used = f"{provider}:deferred"

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
            processed += 1
        await session.commit()
        return processed
