# Analyze Script Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить backend-only pipeline `analyze -> script`, который берет бумаги со статусом `scored`, создает для них summary и черновой русскоязычный short-video script, пишет результат в `paper_summaries` и `scripts`, а затем переводит paper в `scripted`.

**Architecture:** Реализация встраивается в уже существующий job/worker каркас без новых миграций. Новый queue endpoint `POST /jobs/analyze-script-papers` создает DB-backed job и enqueue'ит задачу в текущий dispatcher; worker вызывает новый `AnalyzeScriptService`, который делает deterministic mock generation, затем по возможности enrich'ит результат через LiteLLM и поштучно сохраняет прогресс, не откатывая уже обработанные бумаги при частичных сбоях.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, RQ worker, pytest, LiteLLM provider, existing Postgres schema

---

## File Structure

- Modify: `backend/app/schemas/job.py`
  - Новый request contract для `analyze-script` job.
- Modify: `backend/app/api/jobs.py`
  - Новый endpoint `POST /jobs/analyze-script-papers`.
- Modify: `backend/app/workers/queue.py`
  - Регистрация нового job type в dispatcher map.
- Modify: `backend/app/workers/tasks.py`
  - Новый worker runner для analyze/script job.
- Modify: `backend/app/services/papers.py`
  - Выборка бумаг для analyze/script и upsert helper'ы для summary/script.
- Create: `backend/app/schemas/analyze_script.py`
  - Typed result-модели для mock/enriched draft и scene structure.
- Create: `backend/app/services/analyze_script.py`
  - Основной orchestration service, mock generator и LiteLLM enrichment logic.
- Modify: `backend/tests/test_jobs.py`
  - API-contract test для нового queue endpoint.
- Create: `backend/tests/test_analyze_script.py`
  - Сервисные tests: happy path, mock-only, enrichment failure, per-paper failure, job lifecycle behavior.
- Modify: `backend/tests/conftest.py`
  - При необходимости fixture/helper для вставки бумаг и monkeypatch provider'ов.
- Modify: `README.md`
  - Короткое описание нового pipeline этапа.
- Create: `docs/setup/analyze-script.md`
  - Описание запуска, payload'ов и smoke-проверок.
- Create: `docs/decisions/phase-13-analyze-script-pipeline.md`
  - Зафиксировать решение про staged generation, no migration и partial-progress semantics.

### Task 1: Зафиксировать API и queue-контракт нового job

**Files:**
- Modify: `backend/app/schemas/job.py`
- Modify: `backend/app/api/jobs.py`
- Modify: `backend/app/workers/queue.py`
- Modify: `backend/tests/test_jobs.py`

- [ ] **Step 1: Написать падающий API test на `POST /jobs/analyze-script-papers`**

```python
async def test_analyze_script_jobs_endpoint_returns_tracked_job(
    app_client: AsyncClient,
    isolated_job_dispatcher,
) -> None:
    response = await app_client.post(
        "/jobs/analyze-script-papers",
        json={"limit": 4, "status": "scored", "provider": "litellm"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert UUID(payload["id"])
    assert payload["job_type"] == "analyze-script-papers"
    assert payload["status"] == "queued"
    assert payload["input_json"] == {
        "limit": 4,
        "status": "scored",
        "provider": "litellm",
    }
    assert isolated_job_dispatcher == [
        {
            "job_type": "analyze-script-papers",
            "job_id": payload["id"],
            "payload": {"limit": 4, "status": "scored", "provider": "litellm"},
        }
    ]
```

- [ ] **Step 2: Запустить red phase**

Run: `cd backend; uv run pytest tests/test_jobs.py -q`

Expected: `FAILED`, потому что endpoint и dispatcher mapping для `analyze-script-papers` еще не существуют.

- [ ] **Step 3: Добавить request schema и endpoint**

```python
class AnalyzeScriptJobRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    status: PaperStatus = PaperStatus.SCORED
    provider: str = "mock"
```

```python
@router.post(
    "/jobs/analyze-script-papers",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_analyze_script_job(
    payload: AnalyzeScriptJobRequest,
    session: AsyncSession = Depends(get_session),
    jobs: JobRepository = Depends(get_job_repository),
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobResponse:
    data = payload.model_dump(mode="json")
    job = await jobs.create(session, job_type="analyze-script-papers", payload=data)
    await dispatcher.enqueue("analyze-script-papers", job.id, data)
    return jobs.to_response(job)
```

```python
handlers = {
    "collect-arxiv": run_collect_arxiv_job,
    "score-papers": run_score_papers_job,
    "analyze-script-papers": run_analyze_script_job,
}
```

- [ ] **Step 4: Прогнать API tests и убедиться, что контракт зеленый**

Run: `cd backend; uv run pytest tests/test_jobs.py -q`

Expected: все tests в `tests/test_jobs.py` PASS, включая новый endpoint.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/job.py backend/app/api/jobs.py backend/app/workers/queue.py backend/tests/test_jobs.py
git commit -m "feat: add analyze script job contract"
```

### Task 2: Реализовать deterministic analyze/script service и persistence

**Files:**
- Create: `backend/app/schemas/analyze_script.py`
- Create: `backend/app/services/analyze_script.py`
- Modify: `backend/app/services/papers.py`
- Create: `backend/tests/test_analyze_script.py`

- [ ] **Step 1: Написать падающие сервисные tests на mock-only happy path**

```python
@pytest.mark.asyncio
async def test_analyze_script_service_creates_summary_script_and_marks_paper_scripted(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.10001v1",
            title="Quantum battery breakthrough",
            abstract="A concise abstract for script generation.",
            authors=["Alice", "Bob"],
            categories=["quant-ph"],
            pdf_url="https://arxiv.org/pdf/2606.10001v1",
            published_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "analyze-script"},
            status=PaperStatus.SCORED,
        )
        session.add(paper)
        await session.commit()

        service = AnalyzeScriptService(settings, PaperRepository(), ProviderRegistry(settings))
        processed = await service.process_papers(session, limit=1, status=PaperStatus.SCORED, provider="mock")

    async with session_factory() as session:
        refreshed = await session.get(Paper, paper.id)
        summary = await session.scalar(select(PaperSummary).where(PaperSummary.paper_id == paper.id))
        script = await session.scalar(select(Script).where(Script.paper_id == paper.id))

    assert processed == 1
    assert refreshed is not None
    assert refreshed.status == PaperStatus.SCRIPTED
    assert summary is not None
    assert summary.model_used == "mock:script-draft-v1"
    assert script is not None
    assert script.format == "short-video"
    assert script.language == "ru"
    assert isinstance(script.scene_json, dict)
    assert len(script.scene_json["scenes"]) >= 3
```

- [ ] **Step 2: Запустить red phase**

Run: `cd backend; uv run pytest tests/test_analyze_script.py -q`

Expected: `FAILED`, потому что сервис, schema result'ов и helper'ы persistence еще не реализованы.

- [ ] **Step 3: Добавить typed result models и mock generator**

```python
class SceneDraft(BaseModel):
    scene_number: int
    purpose: str
    narration: str
    visual_cue: str


class AnalyzeScriptDraft(BaseModel):
    technical_summary: str
    popular_summary: str
    limitations: str
    hype_risks: str
    script_text: str
    scenes: list[SceneDraft]
    model_used: str
```

```python
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
                SceneDraft(scene_number=1, purpose="hook", narration=f"Новая статья: {title}", visual_cue="title-card"),
                SceneDraft(scene_number=2, purpose="explain", narration=abstract[:280], visual_cue="paper-diagram"),
                SceneDraft(scene_number=3, purpose="reality-check", narration="Что это меняет и где есть ограничения.", visual_cue="pros-cons"),
            ],
            model_used="mock:script-draft-v1",
        )
```

- [ ] **Step 4: Реализовать service orchestration и upsert helper'ы**

```python
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
```

```python
async def save_generated_content(
    self,
    session: AsyncSession,
    *,
    paper: Paper,
    draft: AnalyzeScriptDraft,
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
```

```python
class AnalyzeScriptService:
    async def process_papers(
        self,
        session: AsyncSession,
        *,
        limit: int,
        status: PaperStatus,
        provider: str,
    ) -> int:
        papers = await self.paper_repository.fetch_for_scripting(session, limit=limit, status=status)
        processed = 0
        for paper in papers:
            draft = self.mock_generator.build(paper)
            await self.paper_repository.save_generated_content(session, paper=paper, draft=draft)
            processed += 1
        return processed
```

- [ ] **Step 5: Прогнать новый test file и commit**

Run: `cd backend; uv run pytest tests/test_analyze_script.py -q`

Expected: PASS для базового mock-only path.

```bash
git add backend/app/schemas/analyze_script.py backend/app/services/analyze_script.py backend/app/services/papers.py backend/tests/test_analyze_script.py
git commit -m "feat: add mock analyze script pipeline"
```

### Task 3: Добавить LiteLLM enrichment и partial-progress semantics

**Files:**
- Modify: `backend/app/services/analyze_script.py`
- Modify: `backend/tests/test_analyze_script.py`
- Modify: `backend/app/workers/tasks.py`

- [ ] **Step 1: Написать падающие tests на enrichment success и enrichment failure**

```python
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
            return '''
            {
              "technical_summary": "Уточненный технический summary.",
              "popular_summary": "Уточненное человеческое объяснение.",
              "limitations": "Уточненные ограничения.",
              "hype_risks": "Уточненные hype risks.",
              "script_text": "Готовый улучшенный сценарий.",
              "scenes": [
                {"scene_number": 1, "purpose": "hook", "narration": "Сцена 1", "visual_cue": "hook"},
                {"scene_number": 2, "purpose": "core", "narration": "Сцена 2", "visual_cue": "diagram"},
                {"scene_number": 3, "purpose": "close", "narration": "Сцена 3", "visual_cue": "takeaway"}
              ]
            }
            '''

        monkeypatch.setattr(provider, "generate", fake_generate)

        service = AnalyzeScriptService(settings, PaperRepository(), registry)
        processed = await service.process_papers(session, limit=1, status=PaperStatus.SCORED, provider="litellm")

    assert processed == 1
```

```python
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
        processed = await service.process_papers(session, limit=1, status=PaperStatus.SCORED, provider="litellm")

    assert processed == 1
```

- [ ] **Step 2: Запустить red phase**

Run: `cd backend; uv run pytest tests/test_analyze_script.py -q`

Expected: `FAILED`, потому что enrichment logic и fallback semantics еще не реализованы.

- [ ] **Step 3: Реализовать JSON enrichment поверх mock draft**

```python
async def _enrich_with_litellm(self, draft: AnalyzeScriptDraft) -> AnalyzeScriptDraft:
    provider = self.provider_registry.get_llm_provider("litellm")
    response = await provider.generate(
        prompt=build_enrichment_prompt(draft),
        model=self.settings.litellm_scoring_model,
    )
    payload = AnalyzeScriptDraft.model_validate_json(response)
    return payload.model_copy(update={"model_used": "gpu/deep-analysis"})
```

```python
for paper in papers:
    try:
        draft = self.mock_generator.build(paper)
        if provider == "litellm":
            try:
                enriched = await self._enrich_with_litellm(draft)
            except (ProviderNotReadyError, ValidationError, ValueError):
                enriched = draft
            await self.paper_repository.save_generated_content(session, paper=paper, draft=enriched)
        else:
            await self.paper_repository.save_generated_content(session, paper=paper, draft=draft)
        processed += 1
    except Exception:
        paper.status = PaperStatus.FAILED
        await session.commit()
```

- [ ] **Step 4: Подключить worker runner и job output**

```python
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
            processed = await service.process_papers(
                session,
                limit=payload.get("limit", 10),
                status=payload.get("status", "scored"),
                provider=payload.get("provider", "mock"),
            )
            await jobs.mark_succeeded(session, job_id, {"processed": processed})
        except Exception as exc:
            await jobs.mark_failed(session, job_id, str(exc))
    await session_manager.dispose()
```

- [ ] **Step 5: Прогнать targeted tests и commit**

Run: `cd backend; uv run pytest tests/test_analyze_script.py tests/test_jobs.py -q`

Expected: PASS, включая mock-only и litellm fallback scenarios.

```bash
git add backend/app/services/analyze_script.py backend/app/workers/tasks.py backend/tests/test_analyze_script.py backend/tests/test_jobs.py
git commit -m "feat: add litellm enrichment for analyze script pipeline"
```

### Task 4: Закрыть docs и end-to-end verification

**Files:**
- Modify: `README.md`
- Create: `docs/setup/analyze-script.md`
- Create: `docs/decisions/phase-13-analyze-script-pipeline.md`

- [ ] **Step 1: Зафиксировать документацию по новой фазе**

```md
## Analyze Script Pipeline

Новый backend job `POST /jobs/analyze-script-papers` берет бумаги со статусом `scored`
и создает для них:

- запись в `paper_summaries`;
- запись в `scripts`;
- `scene_json` c минимальной структурой сцен;
- переход бумаги в `scripted`.

Payload по умолчанию:

`{"limit":10,"status":"scored","provider":"mock"}`
```

- [ ] **Step 2: Прогнать полный backend suite**

Run: `cd backend; uv run pytest -q`

Expected: весь backend suite PASS, включая новый analyze/script слой.

- [ ] **Step 3: Выполнить локальный smoke через API**

Run: `cd backend; uv run python ..\\scripts\\init_db.py`

Expected: БД инициализирована без ошибок.

Run: `curl -X POST http://localhost:8000/jobs/analyze-script-papers -H "Content-Type: application/json" -d "{\"limit\":1,\"status\":\"scored\",\"provider\":\"mock\"}"`

Expected: `202 Accepted` и `job_type=analyze-script-papers`.

Run: `curl http://localhost:8000/jobs`

Expected: в списке есть job со статусом `queued/running/succeeded`, а после завершения в БД появляется paper со статусом `scripted`.

- [ ] **Step 4: При наличии доступа прогнать remote smoke на `sci-docker`**

Run: `ssh alex@192.168.88.150 "cd /home/alex/science-pub && docker compose up -d --build backend worker"`

Expected: `backend` и `worker` в состоянии `running`/`healthy`.

Run: `ssh alex@192.168.88.150 "curl -fsS -X POST http://127.0.0.1:8000/jobs/analyze-script-papers -H 'Content-Type: application/json' -d '{\"limit\":1,\"status\":\"scored\",\"provider\":\"mock\"}'"`

Expected: JSON-ответ с `job_type=analyze-script-papers`.

- [ ] **Step 5: Commit документацию**

```bash
git add README.md docs/setup/analyze-script.md docs/decisions/phase-13-analyze-script-pipeline.md docs/superpowers/plans/2026-06-14-analyze-script-pipeline.md
git commit -m "docs: add analyze script pipeline plan and docs"
```

## Self-Review

- Спецификация покрыта: есть отдельные задачи на queue endpoint, worker task, deterministic mock generation, optional LiteLLM enrichment, persistence в `paper_summaries`/`scripts`, partial-progress semantics, tests и docs.
- Placeholder scan: в плане нет `TODO`/`TBD`; шаги содержат точные файлы, команды, тесты и commit points.
- Type consistency: job type везде одинаковый (`analyze-script-papers`), default status везде `scored`, итоговый paper status везде `scripted`, формат script везде `short-video`, язык везде `ru`.
