# Review Ready RU Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить detail-панель review dashboard в editor-ready поверхность, где кнопка `Analyze Script` запускает подготовку одной выбранной статьи, а после завершения UI показывает нормализованный русский слой `RU Title + RU Abstract + Summary` вместе с уже существующими editorial actions.

**Architecture:** Реализация делится на два слоя. Backend получает явный single-paper analyze contract, сохраняет review-ready русский слой рядом с уже существующими analyze/script артефактами и расширяет detail endpoint вложенным `review_draft` блоком. Frontend detail-панель перестраивается вокруг этого блока: до запуска показывает CTA и raw source, во время выполнения poll'ит job, после успеха рендерит RU draft как primary content и сохраняет `Approve` / `Reject` как следующий editorial шаг.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, Alembic, RQ worker, React, TypeScript, Vite, Vitest, React Testing Library, pytest

---

## File Structure

- Modify: `backend/app/models/paper.py`
  - Расширение `PaperSummary` явными полями review-ready русского слоя.
- Create: `backend/alembic/versions/0002_review_ready_ru_fields.py`
  - Миграция под новые nullable columns в `paper_summaries`.
- Create: `backend/app/schemas/review_ready.py`
  - Typed schema для `ReviewDraftResponse`.
- Modify: `backend/app/schemas/paper.py`
  - Вложенный `review_draft` блок в `PaperResponse`.
- Modify: `backend/app/schemas/job.py`
  - Single-paper request contract для analyze-script job.
- Modify: `backend/app/services/papers.py`
  - Выборка paper по `paper_id`, маппинг latest summary/script в detail response, upsert review-ready content.
- Modify: `backend/app/services/analyze_script.py`
  - Генерация `ru_title`, `ru_abstract`, `summary`, single-paper path и LiteLLM enrichment поверх review-ready draft.
- Modify: `backend/app/api/jobs.py`
  - Endpoint принимает payload для одной выбранной paper.
- Modify: `backend/app/workers/tasks.py`
  - Runner прокидывает `paper_id` и возвращает `processed`/`paper_id` в output.
- Modify: `backend/tests/test_analyze_script.py`
  - Single-paper, RU normalization и fallback semantics.
- Modify: `backend/tests/test_jobs.py`
  - Job endpoint contract с `paper_id`.
- Create: `backend/tests/test_paper_detail_api.py`
  - Detail API contract с `review_draft`.
- Modify: `dashboard/src/lib/types.ts`
  - Типы `ReviewDraft`, `AnalyzeScriptJobRequest`, detail state.
- Modify: `dashboard/src/lib/api.ts`
  - HTTP helper для analyze-script job.
- Modify: `dashboard/src/components/PaperDetail.tsx`
  - RU review block, CTA, loading/error/success states и original source block.
- Modify: `dashboard/src/App.tsx`
  - Orchestration запуска analyze-script для selected paper и refresh detail/list.
- Modify: `dashboard/src/App.test.tsx`
  - Detail workflow tests.
- Modify: `dashboard/src/styles.css`
  - Стили для review-ready section, hints и action states.
- Modify: `README.md`
  - Краткое описание review-ready editorial flow.
- Modify: `docs/setup/analyze-script.md`
  - Update под single-paper review UI use case.
- Modify: `docs/setup/review-dashboard.md`
  - Новый detail workflow.
- Create: `docs/decisions/phase-14-review-ready-ru-detail.md`
  - Фиксация one-click editorial analyze и `review_draft` contract.

### Task 1: Расширить backend schema и detail contract под review-ready русский слой

**Files:**
- Modify: `backend/app/models/paper.py`
- Create: `backend/alembic/versions/0002_review_ready_ru_fields.py`
- Create: `backend/app/schemas/review_ready.py`
- Modify: `backend/app/schemas/paper.py`
- Create: `backend/tests/test_paper_detail_api.py`

- [ ] **Step 1: Написать падающий API test на detail response с `review_draft`**

```python
@pytest.mark.asyncio
async def test_get_paper_returns_review_ready_draft_when_available(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.20001v1",
            title="Original title",
            abstract="Original abstract",
            authors=["Editor"],
            categories=["cs.AI"],
            pdf_url="https://example.invalid/paper.pdf",
            published_at=datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "detail"},
            status=PaperStatus.SCRIPTED,
        )
        session.add(paper)
        await session.flush()
        session.add(
            PaperSummary(
                paper_id=paper.id,
                normalized_title_ru="Нормализованный заголовок",
                normalized_abstract_ru="Нормализованный абстракт",
                short_summary_ru="Короткое summary для редактора.",
                technical_summary="Tech summary",
                popular_summary="Popular summary",
                limitations="Limitations",
                hype_risks="Hype risks",
                model_used="gpu/deep-analysis",
            )
        )
        await session.commit()

    response = await app_client.get(f"/papers/{paper.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["review_draft"] == {
        "ru_title": "Нормализованный заголовок",
        "ru_abstract": "Нормализованный абстракт",
        "summary": "Короткое summary для редактора.",
        "model_used": "gpu/deep-analysis",
    }
```

- [ ] **Step 2: Запустить red phase**

Run: `cd backend; uv run pytest tests/test_paper_detail_api.py -q`

Expected: `FAILED`, потому что `review_draft` поля и schema еще не существуют.

- [ ] **Step 3: Добавить модель, миграцию и response schema**

```python
class PaperSummary(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "paper_summaries"

    paper_id: Mapped[UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    normalized_title_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_abstract_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_summary_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    popular_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    hype_risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

```python
def upgrade() -> None:
    op.add_column("paper_summaries", sa.Column("normalized_title_ru", sa.Text(), nullable=True))
    op.add_column("paper_summaries", sa.Column("normalized_abstract_ru", sa.Text(), nullable=True))
    op.add_column("paper_summaries", sa.Column("short_summary_ru", sa.Text(), nullable=True))
```

```python
class ReviewDraftResponse(BaseModel):
    ru_title: str
    ru_abstract: str
    summary: str
    model_used: str | None = None
```

```python
class PaperResponse(BaseModel):
    id: UUID
    source: str
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    pdf_url: str | None
    published_at: datetime
    collected_at: datetime
    status: PaperStatus
    raw_metadata_json: dict
    latest_score: LatestScore | None = None
    review_draft: ReviewDraftResponse | None = None
```

- [ ] **Step 4: Протянуть `review_draft` в repo mapping**

```python
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
```

```python
return PaperResponse(
    id=cast(UUID, paper.id),
    source=paper.source,
    source_id=paper.source_id,
    title=paper.title,
    abstract=paper.abstract,
    authors=list(paper.authors or []),
    categories=list(paper.categories or []),
    pdf_url=paper.pdf_url,
    published_at=paper.published_at,
    collected_at=paper.collected_at,
    status=paper.status,
    raw_metadata_json=dict(paper.raw_metadata_json or {}),
    latest_score=latest_score,
    review_draft=self._latest_review_draft(paper),
)
```

- [ ] **Step 5: Прогнать API test и commit**

Run: `cd backend; uv run pytest tests/test_paper_detail_api.py -q`

Expected: PASS, detail endpoint возвращает `review_draft` при наличии.

```bash
git add backend/app/models/paper.py backend/alembic/versions/0002_review_ready_ru_fields.py backend/app/schemas/review_ready.py backend/app/schemas/paper.py backend/app/services/papers.py backend/tests/test_paper_detail_api.py
git commit -m "feat: add review-ready detail schema"
```

### Task 2: Сделать single-paper analyze path и RU normalization в backend

**Files:**
- Modify: `backend/app/schemas/job.py`
- Modify: `backend/app/services/papers.py`
- Modify: `backend/app/services/analyze_script.py`
- Modify: `backend/app/api/jobs.py`
- Modify: `backend/app/workers/tasks.py`
- Modify: `backend/tests/test_jobs.py`
- Modify: `backend/tests/test_analyze_script.py`

- [ ] **Step 1: Написать падающий jobs API test на single-paper payload**

```python
async def test_analyze_script_jobs_endpoint_accepts_paper_id(
    app_client: AsyncClient,
    isolated_job_dispatcher,
) -> None:
    paper_id = "11111111-1111-1111-1111-111111111111"

    response = await app_client.post(
        "/jobs/analyze-script-papers",
        json={"paper_id": paper_id, "provider": "mock"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["input_json"] == {
        "paper_id": paper_id,
        "limit": 1,
        "status": "scored",
        "provider": "mock",
    }
```

- [ ] **Step 2: Написать падающий service test на RU normalization для одной paper**

```python
@pytest.mark.asyncio
async def test_analyze_script_service_creates_review_ready_ru_fields_for_single_paper(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = make_scored_paper(
            source_id="2606.20002v1",
            title="Original English title",
        )
        session.add(paper)
        await session.commit()

        service = AnalyzeScriptService(settings, PaperRepository(), ProviderRegistry(settings))
        processed = await service.process_papers(
            session,
            limit=1,
            status=PaperStatus.SCORED,
            provider="mock",
            paper_id=paper.id,
        )

    async with session_factory() as session:
        summary = await session.scalar(select(PaperSummary).where(PaperSummary.paper_id == paper.id))

    assert processed == 1
    assert summary is not None
    assert summary.normalized_title_ru
    assert summary.normalized_abstract_ru
    assert summary.short_summary_ru
```

- [ ] **Step 3: Запустить red phase**

Run: `cd backend; uv run pytest tests/test_jobs.py tests/test_analyze_script.py -q`

Expected: `FAILED`, потому что `paper_id` и RU review fields еще не участвуют в analyze path.

- [ ] **Step 4: Добавить request contract и repo helper для одной paper**

```python
class AnalyzeScriptJobRequest(BaseModel):
    paper_id: UUID | None = None
    limit: int = Field(default=10, ge=1, le=100)
    status: PaperStatus = PaperStatus.SCORED
    provider: str = "mock"
```

```python
async def fetch_for_scripting(
    self,
    session: AsyncSession,
    *,
    limit: int,
    status: PaperStatus,
    paper_id: UUID | None = None,
) -> list[Paper]:
    statement = select(Paper)
    if paper_id is not None:
        statement = statement.where(Paper.id == paper_id)
    else:
        statement = statement.where(Paper.status == status)
    statement = statement.order_by(Paper.published_at.desc()).limit(limit)
    return list((await session.scalars(statement)).all())
```

- [ ] **Step 5: Расширить draft model и mock generator под русский review layer**

```python
class AnalyzeScriptDraft(BaseModel):
    ru_title: str
    ru_abstract: str
    summary: str
    technical_summary: str
    popular_summary: str
    limitations: str
    hype_risks: str
    script_text: str
    scenes: list[SceneDraft]
    model_used: str
```

```python
return AnalyzeScriptDraft(
    ru_title=f"RU: {title}",
    ru_abstract=f"Кратко по-русски: {abstract[:220]}",
    summary=f"Исследование '{title}' предлагает понятный сюжет для редакторского review.",
    technical_summary=f"Работа из категории {category}. Ключевая идея: {abstract[:220]}",
    popular_summary=f"Если коротко, исследователи предлагают новый взгляд на тему '{title}'.",
    limitations="Результат опирается на условия и допущения, описанные авторами статьи.",
    hype_risks="Нельзя автоматически считать, что результат уже готов к массовому применению.",
    script_text=(
        f"Сегодня разберем исследование '{title}'. "
        "Сначала поймем, что именно сделали авторы, потом где это может быть полезно, "
        "и в конце разберем, почему к выводам стоит относиться аккуратно."
    ),
    scenes=[...],
    model_used="mock:script-draft-v2",
)
```

- [ ] **Step 6: Сохранять RU fields и поддержать single-paper path в worker**

```python
session.add(
    PaperSummary(
        paper_id=paper.id,
        normalized_title_ru=draft.ru_title,
        normalized_abstract_ru=draft.ru_abstract,
        short_summary_ru=draft.summary,
        technical_summary=draft.technical_summary,
        popular_summary=draft.popular_summary,
        limitations=draft.limitations,
        hype_risks=draft.hype_risks,
        model_used=draft.model_used,
    )
)
```

```python
processed = await service.process_papers(
    session,
    limit=payload.get("limit", 10),
    status=payload.get("status", "scored"),
    provider=payload.get("provider", "mock"),
    paper_id=payload.get("paper_id"),
)
await jobs.mark_succeeded(
    session,
    job_id,
    {"processed": processed, "paper_id": payload.get("paper_id")},
)
```

- [ ] **Step 7: Прогнать targeted tests и commit**

Run: `cd backend; uv run pytest tests/test_jobs.py tests/test_analyze_script.py tests/test_paper_detail_api.py -q`

Expected: PASS, включая single-paper analyze и detail-ready RU layer.

```bash
git add backend/app/schemas/job.py backend/app/services/papers.py backend/app/services/analyze_script.py backend/app/api/jobs.py backend/app/workers/tasks.py backend/tests/test_jobs.py backend/tests/test_analyze_script.py
git commit -m "feat: add single-paper review-ready analyze flow"
```

### Task 3: Обновить dashboard detail panel под review-ready RU workflow

**Files:**
- Modify: `dashboard/src/lib/types.ts`
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/components/PaperDetail.tsx`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/App.test.tsx`
- Modify: `dashboard/src/styles.css`

- [ ] **Step 1: Написать падающий frontend test на CTA `Analyze Script` и success refresh**

```tsx
it("runs analyze script for selected paper and shows review-ready russian draft", async () => {
  const rawPaper = buildPaper({
    id: "paper-1",
    title: "Original English title",
    abstract: "Original abstract",
    status: "scored",
    review_draft: null,
  });

  const readyPaper = buildPaper({
    id: "paper-1",
    title: "Original English title",
    abstract: "Original abstract",
    status: "scripted",
    review_draft: {
      ru_title: "Нормализованный заголовок",
      ru_abstract: "Нормализованный абстракт",
      summary: "Короткое summary для редактора.",
      model_used: "mock:script-draft-v2",
    },
  });

  let detailCalls = 0;
  let jobsCalls = 0;

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.includes("/api/papers?")) {
      return new Response(JSON.stringify({ total: 1, limit: 25, offset: 0, items: [rawPaper] }), {
        status: 200,
      });
    }

    if (url.endsWith("/api/papers/paper-1")) {
      detailCalls += 1;
      return new Response(JSON.stringify(detailCalls >= 2 ? readyPaper : rawPaper), { status: 200 });
    }

    if (url.endsWith("/api/jobs/analyze-script-papers")) {
      expect(init?.method).toBe("POST");
      return new Response(
        JSON.stringify({
          id: "analyze-job",
          job_type: "analyze-script-papers",
          status: "queued",
          input_json: { paper_id: "paper-1", limit: 1, status: "scored", provider: "mock" },
          output_json: null,
          error_text: null,
          created_at: "2026-06-14T17:00:00Z",
          updated_at: "2026-06-14T17:00:00Z",
        }),
        { status: 202 },
      );
    }

    if (url.endsWith("/api/jobs")) {
      jobsCalls += 1;
      return new Response(
        JSON.stringify([
          {
            id: "analyze-job",
            job_type: "analyze-script-papers",
            status: jobsCalls === 1 ? "running" : "succeeded",
            input_json: { paper_id: "paper-1", limit: 1, status: "scored", provider: "mock" },
            output_json: jobsCalls === 1 ? null : { processed: 1, paper_id: "paper-1" },
            error_text: null,
            created_at: "2026-06-14T17:00:00Z",
            updated_at: "2026-06-14T17:00:05Z",
          },
        ]),
        { status: 200 },
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: /original english title/i }));
  expect(await screen.findByRole("button", { name: /analyze script/i })).toBeInTheDocument();

  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /analyze script/i }));
  });

  expect(await screen.findByText(/preparing russian review draft/i)).toBeInTheDocument();

  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

  expect(await screen.findByText(/нормализованный заголовок/i)).toBeInTheDocument();
  expect(screen.getByText(/короткое summary для редактора/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Запустить red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: `FAILED`, потому что UI еще не знает про `review_draft`, analyze button и detail refresh flow.

- [ ] **Step 3: Добавить типы и API helper**

```ts
export interface ReviewDraft {
  ru_title: string;
  ru_abstract: string;
  summary: string;
  model_used: string | null;
}

export interface Paper {
  id: string;
  source: string;
  source_id: string;
  title: string;
  abstract: string;
  authors: string[];
  categories: string[];
  pdf_url: string | null;
  published_at: string;
  collected_at: string;
  status: PaperStatus;
  raw_metadata_json: Record<string, unknown>;
  latest_score: LatestScore | null;
  review_draft: ReviewDraft | null;
}

export interface AnalyzeScriptJobRequest {
  paper_id: string;
  limit?: number;
  status?: PaperStatus;
  provider?: string;
}
```

```ts
export async function enqueueAnalyzeScriptJob(payload: AnalyzeScriptJobRequest): Promise<JobRecord> {
  const response = await fetch("/api/jobs/analyze-script-papers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      paper_id: payload.paper_id,
      limit: payload.limit ?? 1,
      status: payload.status ?? "scored",
      provider: payload.provider ?? "mock",
    }),
  });

  if (!response.ok) {
    throw new Error("analyze_script_job_failed");
  }

  return response.json() as Promise<JobRecord>;
}
```

- [ ] **Step 4: Перестроить `PaperDetail` вокруг `review_draft`**

```tsx
interface PaperDetailProps {
  busy: boolean;
  loading: boolean;
  analyzeBusy: boolean;
  analyzeError: string | null;
  onAnalyze: () => void;
  onApprove: () => void;
  onReject: () => void;
  paper: Paper | null;
}
```

```tsx
{paper.review_draft ? (
  <section className="detail__review-draft">
    <div className="detail__section-header">
      <h3>Review Draft</h3>
      <span className="detail__draft-state">Review Draft Ready</span>
    </div>
    <div className="detail__draft-block">
      <dt>RU Title</dt>
      <dd>{paper.review_draft.ru_title}</dd>
    </div>
    <div className="detail__draft-block">
      <dt>RU Abstract</dt>
      <dd>{paper.review_draft.ru_abstract}</dd>
    </div>
    <div className="detail__draft-block">
      <dt>Summary</dt>
      <dd>{paper.review_draft.summary}</dd>
    </div>
  </section>
) : (
  <section className="detail__review-empty">
    <h3>Review Draft</h3>
    <p>Подготовьте нормализованный русский слой перед редакторской оценкой.</p>
    <button type="button" onClick={onAnalyze} disabled={busy || analyzeBusy}>
      Analyze Script
    </button>
  </section>
)}
```

- [ ] **Step 5: Добавить orchestration в `App.tsx`**

```tsx
const [analyzeBusy, setAnalyzeBusy] = useState(false);
const [analyzeMessage, setAnalyzeMessage] = useState<string | null>(null);

async function runAnalyzeScript() {
  if (!selectedPaperId) {
    return;
  }

  setAnalyzeBusy(true);
  setAnalyzeMessage("Preparing Russian review draft...");

  try {
    const job = await enqueueAnalyzeScriptJob({ paper_id: selectedPaperId });
    await waitForJob(job.id);
    await loadPapers(filters, { preserveSelection: true });
    const refreshedPaper = await getPaper(selectedPaperId);
    setSelectedPaper(refreshedPaper);
    setAnalyzeMessage(null);
  } catch (analyzeError) {
    setAnalyzeMessage(
      analyzeError instanceof Error ? analyzeError.message : "Analyze script failed",
    );
  } finally {
    setAnalyzeBusy(false);
  }
}
```

- [ ] **Step 6: Прогнать frontend tests и build, затем commit**

Run: `npm --prefix dashboard test -- --run`

Expected: PASS, включая новый detail analyze workflow.

Run: `npm --prefix dashboard run build`

Expected: build succeeds.

```bash
git add dashboard/src/lib/types.ts dashboard/src/lib/api.ts dashboard/src/components/PaperDetail.tsx dashboard/src/App.tsx dashboard/src/App.test.tsx dashboard/src/styles.css
git commit -m "feat: add review-ready detail workflow"
```

### Task 4: Закрыть docs и full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/setup/analyze-script.md`
- Modify: `docs/setup/review-dashboard.md`
- Create: `docs/decisions/phase-14-review-ready-ru-detail.md`
- Modify: `docs/superpowers/plans/2026-06-14-review-ready-ru-detail.md`

- [ ] **Step 1: Обновить документацию под новый editorial flow**

```md
## Review-Ready Detail

В detail-панели dashboard кнопка `Analyze Script` работает по одной выбранной paper.
После успеха редактор видит:

- `RU Title`
- `RU Abstract`
- `Summary`

Original source остается доступным как reference block.
```

- [ ] **Step 2: Прогнать полный backend suite**

Run: `cd backend; uv run pytest -q`

Expected: весь backend suite PASS.

- [ ] **Step 3: Прогнать полный frontend suite**

Run: `npm --prefix dashboard test -- --run`

Expected: весь dashboard suite PASS.

Run: `npm --prefix dashboard run build`

Expected: build succeeds.

- [ ] **Step 4: Выполнить smoke локально или на `sci-docker`**

Run: `curl -X POST http://localhost:8000/jobs/analyze-script-papers -H "Content-Type: application/json" -d "{\"paper_id\":\"<paper-id>\",\"provider\":\"mock\"}"`

Expected: `202 Accepted`, job создается с `paper_id`.

Run: `curl http://localhost:8000/papers/<paper-id>`

Expected: detail payload содержит `review_draft`.

Run: `curl http://localhost:3000`

Expected: dashboard грузится; после выбора paper и analyze flow в detail появляется review-ready русский блок.

- [ ] **Step 5: Commit документацию**

```bash
git add README.md docs/setup/analyze-script.md docs/setup/review-dashboard.md docs/decisions/phase-14-review-ready-ru-detail.md docs/superpowers/plans/2026-06-14-review-ready-ru-detail.md
git commit -m "docs: add review-ready detail workflow"
```

## Self-Review

- Spec coverage: план покрывает single-paper entrypoint, RU normalization, review-ready detail contract, CTA/status UX, original source reference, frontend detail workflow, tests и docs.
- Placeholder scan: в плане нет `TODO`/`TBD`; у каждого task есть конкретные файлы, тесты, команды и commit points.
- Type consistency: везде используется `review_draft`, single-paper payload идет через `paper_id`, analyze action называется `Analyze Script`, итоговый generated UI layer везде состоит из `ru_title`, `ru_abstract`, `summary`.
