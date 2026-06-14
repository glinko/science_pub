from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppSettings
from app.enums import PaperStatus
from app.models.paper import Paper
from app.providers.litellm_provider import ProviderNotReadyError
from app.providers.registry import ProviderRegistry
from app.schemas.analyze_script import AnalyzeScriptDraft, SceneDraft

from .papers import PaperRepository


class MockAnalyzeScriptGenerator:
    def build(self, paper: Paper) -> AnalyzeScriptDraft:
        title = paper.title.strip()
        abstract = paper.abstract.strip()
        category = paper.categories[0] if paper.categories else "science"
        return AnalyzeScriptDraft(
            technical_summary=f"Работа из категории {category}. Ключевая идея: {abstract[:220]}",
            popular_summary=f"Если коротко, исследователи предлагают новый взгляд на тему '{title}'.",
            limitations="Результат опирается на условия и допущения, описанные авторами статьи.",
            hype_risks="Нельзя автоматически считать, что результат уже готов к массовому применению.",
            script_text=(
                f"Сегодня разберем исследование '{title}'. "
                "Сначала поймем, что именно сделали авторы, потом где это может быть полезно, "
                "и в конце разберем, почему к выводам стоит относиться аккуратно."
            ),
            scenes=[
                SceneDraft(
                    scene_number=1,
                    purpose="hook",
                    narration=f"Новая статья: {title}",
                    visual_cue="title-card",
                ),
                SceneDraft(
                    scene_number=2,
                    purpose="explain",
                    narration=abstract[:280],
                    visual_cue="paper-diagram",
                ),
                SceneDraft(
                    scene_number=3,
                    purpose="reality-check",
                    narration="Что это меняет и где есть ограничения.",
                    visual_cue="pros-cons",
                ),
            ],
            model_used="mock:script-draft-v1",
        )


class AnalyzeScriptService:
    def __init__(
        self,
        settings: AppSettings,
        paper_repository: PaperRepository,
        provider_registry: ProviderRegistry,
    ) -> None:
        self.settings = settings
        self.paper_repository = paper_repository
        self.provider_registry = provider_registry
        self.mock_generator = MockAnalyzeScriptGenerator()

    def _build_enrichment_prompt(self, draft: AnalyzeScriptDraft) -> str:
        return (
            "Ты улучшаешь черновик научпоп-сценария. "
            "Верни только JSON с полями technical_summary, popular_summary, limitations, "
            "hype_risks, script_text, scenes, model_used. "
            f"Текущий draft: {draft.model_dump_json(ensure_ascii=False)}"
        )

    async def _enrich_with_litellm(self, draft: AnalyzeScriptDraft) -> AnalyzeScriptDraft:
        provider = self.provider_registry.get_llm_provider("litellm")
        response = await provider.generate(
            self._build_enrichment_prompt(draft),
            model=self.settings.litellm_scoring_model,
        )
        payload = AnalyzeScriptDraft.model_validate_json(response)
        return payload.model_copy(update={"model_used": self.settings.litellm_scoring_model})

    async def process_papers(
        self,
        session: AsyncSession,
        *,
        limit: int,
        status: PaperStatus,
        provider: str,
    ) -> int:
        papers = await self.paper_repository.fetch_for_scripting(
            session,
            limit=limit,
            status=status,
        )
        processed = 0
        for paper in papers:
            try:
                draft = self.mock_generator.build(paper)
                if provider == "litellm":
                    try:
                        draft = await self._enrich_with_litellm(draft)
                    except (ProviderNotReadyError, ValidationError, ValueError):
                        pass
                await self.paper_repository.save_generated_content(session, paper=paper, draft=draft)
                processed += 1
            except Exception:
                paper.status = PaperStatus.FAILED
                await session.commit()
        return processed
