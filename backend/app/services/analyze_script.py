from __future__ import annotations

from uuid import UUID

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
            ru_title=f"\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a: {title}",
            ru_abstract=f"\u041a\u0440\u0430\u0442\u043a\u043e \u043f\u043e-\u0440\u0443\u0441\u0441\u043a\u0438: {abstract[:220]}",
            summary=(
                f"\u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435 '{title}' "
                "\u0434\u0430\u0435\u0442 \u043f\u043e\u043d\u044f\u0442\u043d\u044b\u0439 \u0441\u044e\u0436\u0435\u0442 "
                "\u0434\u043b\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440\u0441\u043a\u043e\u0439 \u043e\u0446\u0435\u043d\u043a\u0438."
            ),
            technical_summary=(
                f"\u0420\u0430\u0431\u043e\u0442\u0430 \u0438\u0437 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 {category}. "
                f"\u041a\u043b\u044e\u0447\u0435\u0432\u0430\u044f \u0438\u0434\u0435\u044f: {abstract[:220]}"
            ),
            popular_summary=(
                f"\u0415\u0441\u043b\u0438 \u043a\u043e\u0440\u043e\u0442\u043a\u043e, \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u0435\u043b\u0438 "
                f"\u043f\u0440\u0435\u0434\u043b\u0430\u0433\u0430\u044e\u0442 \u043d\u043e\u0432\u044b\u0439 \u0432\u0437\u0433\u043b\u044f\u0434 "
                f"\u043d\u0430 \u0442\u0435\u043c\u0443 '{title}'."
            ),
            limitations=(
                "\u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u043e\u043f\u0438\u0440\u0430\u0435\u0442\u0441\u044f "
                "\u043d\u0430 \u0443\u0441\u043b\u043e\u0432\u0438\u044f \u0438 \u0434\u043e\u043f\u0443\u0449\u0435\u043d\u0438\u044f, "
                "\u043e\u043f\u0438\u0441\u0430\u043d\u043d\u044b\u0435 \u0430\u0432\u0442\u043e\u0440\u0430\u043c\u0438 \u0441\u0442\u0430\u0442\u044c\u0438."
            ),
            hype_risks=(
                "\u041d\u0435\u043b\u044c\u0437\u044f \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 "
                "\u0441\u0447\u0438\u0442\u0430\u0442\u044c, \u0447\u0442\u043e \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 "
                "\u0443\u0436\u0435 \u0433\u043e\u0442\u043e\u0432 \u043a \u043c\u0430\u0441\u0441\u043e\u0432\u043e\u043c\u0443 "
                "\u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u0438\u044e."
            ),
            script_text=(
                f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0440\u0430\u0437\u0431\u0435\u0440\u0435\u043c \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0435 '{title}'. "
                "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u043e\u0439\u043c\u0435\u043c, \u0447\u0442\u043e \u0438\u043c\u0435\u043d\u043d\u043e "
                "\u0441\u0434\u0435\u043b\u0430\u043b\u0438 \u0430\u0432\u0442\u043e\u0440\u044b, \u043f\u043e\u0442\u043e\u043c \u0433\u0434\u0435 "
                "\u044d\u0442\u043e \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043f\u043e\u043b\u0435\u0437\u043d\u043e, \u0438 "
                "\u0432 \u043a\u043e\u043d\u0446\u0435 \u0440\u0430\u0437\u0431\u0435\u0440\u0435\u043c, \u043f\u043e\u0447\u0435\u043c\u0443 "
                "\u043a \u0432\u044b\u0432\u043e\u0434\u0430\u043c \u0441\u0442\u043e\u0438\u0442 "
                "\u043e\u0442\u043d\u043e\u0441\u0438\u0442\u044c\u0441\u044f \u0430\u043a\u043a\u0443\u0440\u0430\u0442\u043d\u043e."
            ),
            scenes=[
                SceneDraft(
                    scene_number=1,
                    purpose="hook",
                    narration=f"\u041d\u043e\u0432\u0430\u044f \u0441\u0442\u0430\u0442\u044c\u044f: {title}",
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
                    narration=(
                        "\u0427\u0442\u043e \u044d\u0442\u043e \u043c\u0435\u043d\u044f\u0435\u0442 \u0438 "
                        "\u0433\u0434\u0435 \u0435\u0441\u0442\u044c \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f."
                    ),
                    visual_cue="pros-cons",
                ),
            ],
            model_used="mock:script-draft-v2",
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
            "\u0422\u044b \u0443\u043b\u0443\u0447\u0448\u0430\u0435\u0448\u044c \u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a "
            "\u043d\u0430\u0443\u0447\u043f\u043e\u043f-\u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f. "
            "\u0412\u0435\u0440\u043d\u0438 \u0442\u043e\u043b\u044c\u043a\u043e JSON \u0441 \u043f\u043e\u043b\u044f\u043c\u0438 "
            "ru_title, ru_abstract, summary, technical_summary, popular_summary, limitations, "
            "hype_risks, script_text, scenes, model_used. "
            f"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 draft: {draft.model_dump_json(ensure_ascii=False)}"
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
        paper_id: UUID | None = None,
    ) -> int:
        papers = await self.paper_repository.fetch_for_scripting(
            session,
            limit=limit,
            status=status,
            paper_id=paper_id,
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
