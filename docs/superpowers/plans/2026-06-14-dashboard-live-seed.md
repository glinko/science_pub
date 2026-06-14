# Dashboard Live Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в review dashboard одну кнопку live-seed, которая запускает `collect-arxiv`, затем `score-papers`, показывает прогресс цепочки и автоматически обновляет список статей.

**Architecture:** Реализация остается frontend-driven: dashboard переиспользует существующие backend endpoints `POST /jobs/collect-arxiv`, `POST /jobs/score-papers` и `GET /jobs`, не вводя новый orchestration endpoint. UI получает небольшой control block в header, локально держит состояние `idle/collecting/scoring/success/failed`, poll'ит job statuses и после успеха повторно загружает `GET /papers` с текущими фильтрами.

**Tech Stack:** React, TypeScript, Vite, Vitest, React Testing Library, FastAPI job endpoints, Docker Compose

---

## File Structure

- Modify: `dashboard/src/lib/types.ts`
  - Типы для `JobStatus`, `JobRecord`, payload'ов collect/score и локального live-seed state.
- Modify: `dashboard/src/lib/api.ts`
  - HTTP helpers для `POST /jobs/collect-arxiv`, `POST /jobs/score-papers`, `GET /jobs`.
- Create: `dashboard/src/components/LiveSeedControl.tsx`
  - Кнопка `Fetch Fresh Papers`, текст текущего этапа и error/success message.
- Modify: `dashboard/src/App.tsx`
  - Orchestration `collect -> score -> refresh`, polling jobs, disable state кнопки и повторная загрузка списка.
- Modify: `dashboard/src/App.test.tsx`
  - TDD-контракты для happy path, failed collect, failed score и авто-refresh.
- Modify: `dashboard/src/styles.css`
  - Стили header control, status chips и disabled/busy states.
- Modify: `README.md`
  - Краткое описание live-seed workflow в dashboard.
- Modify: `docs/setup/review-dashboard.md`
  - Подробное описание кнопки, дефолтных payload'ов и smoke-проверки.
- Create: `docs/decisions/phase-12-dashboard-live-seed.md`
  - Фиксация решения "frontend orchestration без нового backend endpoint".

### Task 1: Добавить jobs API и happy-path orchestration

**Files:**
- Modify: `dashboard/src/lib/types.ts`
- Modify: `dashboard/src/lib/api.ts`
- Create: `dashboard/src/components/LiveSeedControl.tsx`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Написать падающий frontend test на кнопку и успешную цепочку `collect -> score -> refresh`**

```tsx
it("runs collect, then score, then refreshes papers", async () => {
  vi.useFakeTimers();

  const initialPaper = buildPaper({ id: "paper-1", title: "Older paper" });
  const freshPaper = buildPaper({ id: "paper-2", title: "Fresh paper", status: "scored" });

  let papersCalls = 0;
  let jobsCalls = 0;

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);

    if (url.includes("/api/papers?")) {
      papersCalls += 1;
      return new Response(
        JSON.stringify({
          total: papersCalls === 1 ? 1 : 2,
          limit: 25,
          offset: 0,
          items: papersCalls === 1 ? [initialPaper] : [freshPaper, initialPaper],
        }),
        { status: 200 },
      );
    }

    if (url.endsWith("/api/jobs/collect-arxiv")) {
      return new Response(
        JSON.stringify({
          id: "collect-job",
          job_type: "collect-arxiv",
          status: "queued",
          input_json: { categories: [], max_results: 100 },
          output_json: null,
          error_text: null,
          created_at: "2026-06-14T12:00:00Z",
          updated_at: "2026-06-14T12:00:00Z",
        }),
        { status: 202 },
      );
    }

    if (url.endsWith("/api/jobs/score-papers")) {
      return new Response(
        JSON.stringify({
          id: "score-job",
          job_type: "score-papers",
          status: "queued",
          input_json: { limit: 20, status: "collected", provider: "mock" },
          output_json: null,
          error_text: null,
          created_at: "2026-06-14T12:01:00Z",
          updated_at: "2026-06-14T12:01:00Z",
        }),
        { status: 202 },
      );
    }

    if (url.endsWith("/api/jobs")) {
      jobsCalls += 1;

      if (jobsCalls === 1) {
        return new Response(
          JSON.stringify([
            {
              id: "collect-job",
              job_type: "collect-arxiv",
              status: "running",
              input_json: { categories: [], max_results: 100 },
              output_json: null,
              error_text: null,
              created_at: "2026-06-14T12:00:00Z",
              updated_at: "2026-06-14T12:00:05Z",
            },
          ]),
          { status: 200 },
        );
      }

      if (jobsCalls === 2) {
        return new Response(
          JSON.stringify([
            {
              id: "collect-job",
              job_type: "collect-arxiv",
              status: "succeeded",
              input_json: { categories: [], max_results: 100 },
              output_json: { fetched: 15, inserted: 8, duplicates: 7 },
              error_text: null,
              created_at: "2026-06-14T12:00:00Z",
              updated_at: "2026-06-14T12:00:10Z",
            },
          ]),
          { status: 200 },
        );
      }

      if (jobsCalls === 3) {
        return new Response(
          JSON.stringify([
            {
              id: "score-job",
              job_type: "score-papers",
              status: "running",
              input_json: { limit: 20, status: "collected", provider: "mock" },
              output_json: null,
              error_text: null,
              created_at: "2026-06-14T12:01:00Z",
              updated_at: "2026-06-14T12:01:05Z",
            },
          ]),
          { status: 200 },
        );
      }

      return new Response(
        JSON.stringify([
          {
            id: "score-job",
            job_type: "score-papers",
            status: "succeeded",
            input_json: { limit: 20, status: "collected", provider: "mock" },
            output_json: { processed: 8 },
            error_text: null,
            created_at: "2026-06-14T12:01:00Z",
            updated_at: "2026-06-14T12:01:20Z",
          },
        ]),
        { status: 200 },
      );
    }

    throw new Error(`Unexpected request: ${url} ${init?.method ?? "GET"}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  const button = await screen.findByRole("button", { name: /fetch fresh papers/i });
  await userEvent.click(button);

  expect(await screen.findByText(/collecting/i)).toBeInTheDocument();
  expect(button).toBeDisabled();

  await vi.advanceTimersByTimeAsync(5_000);
  expect(await screen.findByText(/scoring/i)).toBeInTheDocument();

  await vi.advanceTimersByTimeAsync(5_000);
  expect(await screen.findByText(/done/i)).toBeInTheDocument();
  expect(await screen.findByText(/fresh paper/i)).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/jobs/collect-arxiv", expect.any(Object));
  expect(fetchMock).toHaveBeenCalledWith("/api/jobs/score-papers", expect.any(Object));
});
```

- [ ] **Step 2: Запустить test и увидеть red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: `FAILED`, потому что кнопка live-seed, jobs API и orchestration еще не существуют.

- [ ] **Step 3: Добавить типы jobs и API helpers**

```ts
export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface JobRecord {
  id: string;
  job_type: string;
  status: JobStatus;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown> | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface CollectJobRequest {
  categories: string[];
  max_results: number;
}

export interface ScoreJobRequest {
  limit: number;
  status: PaperStatus;
  provider: string;
}
```

```ts
export async function enqueueCollectJob(payload: CollectJobRequest): Promise<JobRecord> {
  const response = await fetch("/api/jobs/collect-arxiv", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("collect_job_failed");
  }

  return response.json() as Promise<JobRecord>;
}

export async function enqueueScoreJob(payload: ScoreJobRequest): Promise<JobRecord> {
  const response = await fetch("/api/jobs/score-papers", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("score_job_failed");
  }

  return response.json() as Promise<JobRecord>;
}

export async function listJobs(): Promise<JobRecord[]> {
  const response = await fetch("/api/jobs");

  if (!response.ok) {
    throw new Error("jobs_list_failed");
  }

  return response.json() as Promise<JobRecord[]>;
}
```

- [ ] **Step 4: Реализовать минимальный UI control и happy-path orchestration**

```tsx
export function LiveSeedControl({
  busy,
  stage,
  message,
  onRun,
}: {
  busy: boolean;
  stage: "idle" | "collecting" | "scoring" | "success" | "failed";
  message: string | null;
  onRun: () => void;
}) {
  return (
    <div className="live-seed">
      <button type="button" onClick={onRun} disabled={busy}>
        Fetch Fresh Papers
      </button>
      {stage !== "idle" ? <p className={`live-seed__status live-seed__status--${stage}`}>{message}</p> : null}
    </div>
  );
}
```

```tsx
const POLL_INTERVAL_MS = 2_500;

async function waitForJob(jobId: string) {
  while (true) {
    const jobs = await listJobs();
    const job = jobs.find((item) => item.id === jobId);

    if (!job) {
      throw new Error("job_not_found");
    }

    if (job.status === "succeeded") {
      return job;
    }

    if (job.status === "failed") {
      throw new Error(job.error_text || "job_failed");
    }

    await new Promise((resolve) => window.setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function runLiveSeed() {
  setSeedBusy(true);
  setSeedStage("collecting");
  setSeedMessage("Collecting...");

  try {
    const collectJob = await enqueueCollectJob({ categories: [], max_results: 100 });
    await waitForJob(collectJob.id);

    setSeedStage("scoring");
    setSeedMessage("Scoring...");

    const scoreJob = await enqueueScoreJob({ limit: 20, status: "collected", provider: "mock" });
    await waitForJob(scoreJob.id);

    await loadPapers(filters, { preserveSelection: true });
    setSeedStage("success");
    setSeedMessage("Done");
  } catch (error) {
    setSeedStage("failed");
    setSeedMessage(error instanceof Error ? error.message : "Live seed failed");
  } finally {
    setSeedBusy(false);
  }
}
```

- [ ] **Step 5: Прогнать frontend tests повторно**

Run: `npm --prefix dashboard test -- --run`

Expected: тест на happy path проходит, кнопка disabled во время работы, collect и score job вызываются в нужном порядке, список статей обновляется после успеха.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/lib/types.ts dashboard/src/lib/api.ts dashboard/src/components/LiveSeedControl.tsx dashboard/src/App.tsx dashboard/src/App.test.tsx
git commit -m "feat: add dashboard live seed flow"
```

### Task 2: Закрыть failed states, сообщения UI и сохранение контекста review

**Files:**
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/App.test.tsx`
- Modify: `dashboard/src/styles.css`

- [ ] **Step 1: Написать падающий frontend test на failed collect**

```tsx
it("shows collect failure and does not start scoring", async () => {
  vi.useFakeTimers();

  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes("/api/papers?")) {
      return new Response(JSON.stringify({ total: 0, limit: 25, offset: 0, items: [] }), { status: 200 });
    }

    if (url.endsWith("/api/jobs/collect-arxiv")) {
      return new Response(
        JSON.stringify({
          id: "collect-job",
          job_type: "collect-arxiv",
          status: "queued",
          input_json: { categories: [], max_results: 100 },
          output_json: null,
          error_text: null,
          created_at: "2026-06-14T12:00:00Z",
          updated_at: "2026-06-14T12:00:00Z",
        }),
        { status: 202 },
      );
    }

    if (url.endsWith("/api/jobs")) {
      return new Response(
        JSON.stringify([
          {
            id: "collect-job",
            job_type: "collect-arxiv",
            status: "failed",
            input_json: { categories: [], max_results: 100 },
            output_json: null,
            error_text: "arXiv timeout",
            created_at: "2026-06-14T12:00:00Z",
            updated_at: "2026-06-14T12:00:05Z",
          },
        ]),
        { status: 200 },
      );
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  await userEvent.click(await screen.findByRole("button", { name: /fetch fresh papers/i }));
  await vi.advanceTimersByTimeAsync(3_000);

  expect(await screen.findByText(/arxiv timeout/i)).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalledWith("/api/jobs/score-papers", expect.anything());
});
```

- [ ] **Step 2: Написать падающий frontend test на failed score и сохранение selection при reload**

```tsx
it("shows score failure without pretending refresh succeeded", async () => {
  vi.useFakeTimers();

  const selectedPaper = buildPaper({ id: "paper-1", title: "Selected paper" });
  let papersCalls = 0;
  let jobsCalls = 0;

  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes("/api/papers?")) {
      papersCalls += 1;
      return new Response(
        JSON.stringify({
          total: 1,
          limit: 25,
          offset: 0,
          items: [selectedPaper],
        }),
        { status: 200 },
      );
    }

    if (url.endsWith("/api/papers/paper-1")) {
      return new Response(JSON.stringify(selectedPaper), { status: 200 });
    }

    if (url.endsWith("/api/jobs/collect-arxiv")) {
      return new Response(JSON.stringify({ id: "collect-job", job_type: "collect-arxiv", status: "queued", input_json: {}, output_json: null, error_text: null, created_at: "2026-06-14T12:00:00Z", updated_at: "2026-06-14T12:00:00Z" }), { status: 202 });
    }

    if (url.endsWith("/api/jobs/score-papers")) {
      return new Response(JSON.stringify({ id: "score-job", job_type: "score-papers", status: "queued", input_json: {}, output_json: null, error_text: null, created_at: "2026-06-14T12:01:00Z", updated_at: "2026-06-14T12:01:00Z" }), { status: 202 });
    }

    if (url.endsWith("/api/jobs")) {
      jobsCalls += 1;

      if (jobsCalls === 1) {
        return new Response(JSON.stringify([{ id: "collect-job", job_type: "collect-arxiv", status: "succeeded", input_json: {}, output_json: {}, error_text: null, created_at: "2026-06-14T12:00:00Z", updated_at: "2026-06-14T12:00:05Z" }]), { status: 200 });
      }

      return new Response(JSON.stringify([{ id: "score-job", job_type: "score-papers", status: "failed", input_json: {}, output_json: null, error_text: "mock provider exploded", created_at: "2026-06-14T12:01:00Z", updated_at: "2026-06-14T12:01:05Z" }]), { status: 200 });
    }

    throw new Error(`Unexpected request: ${url}`);
  });

  vi.stubGlobal("fetch", fetchMock);
  render(<App />);

  await userEvent.click(await screen.findByRole("button", { name: /selected paper/i }));
  await userEvent.click(await screen.findByRole("button", { name: /fetch fresh papers/i }));
  await vi.advanceTimersByTimeAsync(6_000);

  expect(await screen.findByText(/mock provider exploded/i)).toBeInTheDocument();
  expect(papersCalls).toBe(1);
  expect(screen.getByText(/selected paper/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Запустить tests и увидеть red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: `FAILED`, потому что failed-ветки и сохранение review context еще не реализованы полностью.

- [ ] **Step 4: Доработать orchestration, сообщения и поведение detail**

```tsx
if (job.status === "failed") {
  throw new Error(job.error_text || `${job.job_type} failed`);
}
```

```tsx
setSeedStage("failed");
setSeedMessage(error instanceof Error ? error.message : "Live seed failed");
```

```tsx
await loadPapers(nextFilters, { preserveSelection: true });
```

```tsx
async function loadPapers(
  nextFilters: typeof filters,
  options: { preserveSelection: boolean },
) {
  const payload = await listPapers(buildPapersQuery(nextFilters));
  setPapers(payload.items);

  if (!options.preserveSelection || !selectedPaperId) {
    return;
  }

  const stillVisible = payload.items.find((paper) => paper.id === selectedPaperId);

  if (stillVisible) {
    setSelectedPaper(stillVisible);
    return;
  }

  setSelectedPaperId(null);
  setSelectedPaper(null);
}
```

```css
.live-seed {
  display: flex;
  align-items: center;
  gap: 12px;
}

.live-seed__status {
  font-size: 14px;
  color: #4b5563;
}

.live-seed__status--failed {
  color: #b42318;
}

.live-seed__status--success {
  color: #027a48;
}
```

- [ ] **Step 5: Прогнать frontend suite повторно**

Run: `npm --prefix dashboard test -- --run`

Expected: happy path, failed collect и failed score tests pass; selection не теряется без необходимости.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/App.tsx dashboard/src/App.test.tsx dashboard/src/styles.css
git commit -m "fix: harden dashboard live seed states"
```

### Task 3: Документация и полная verification

**Files:**
- Modify: `README.md`
- Modify: `docs/setup/review-dashboard.md`
- Create: `docs/decisions/phase-12-dashboard-live-seed.md`

- [ ] **Step 1: Обновить README и setup-документацию**

```md
## Review Dashboard

Dashboard теперь поддерживает live-seed действие `Fetch Fresh Papers`.

Что делает кнопка:
- создает job `collect-arxiv` c payload `{ "categories": [], "max_results": 100 }`;
- после `succeeded` автоматически создает job `score-papers` c payload `{ "limit": 20, "status": "collected", "provider": "mock" }`;
- показывает пользователю этапы `Collecting`, `Scoring`, `Done` или `Failed`;
- после успеха автоматически обновляет список статей.
```

```md
# Phase 12: dashboard live seed

- orchestration выполняется во frontend, а не через новый backend endpoint;
- backend переиспользует существующие `/jobs/collect-arxiv`, `/jobs/score-papers`, `/jobs`;
- первая версия не дает выбора categories/provider из UI и использует defaults milestone 1.
```

- [ ] **Step 2: Прогнать локальные test/build команды**

Run: `npm --prefix dashboard test -- --run`

Run: `npm --prefix dashboard run build`

Run: `uv run pytest -q`

Expected:
- frontend tests pass;
- production build проходит;
- backend suite остается зеленой.

- [ ] **Step 3: Проверить compose-конфиг**

Run: `docker compose config`

Expected: конфигурация валидна, dashboard service не сломан добавлением live-seed UI.

- [ ] **Step 4: Выполнить smoke-проверку UI**

Run: `docker compose up -d --build`

Run: `curl http://localhost:3000`

Run: `curl http://localhost:8000/jobs`

Expected:
- dashboard доступен по `http://localhost:3000`;
- backend jobs endpoint отвечает;
- из браузера кнопка `Fetch Fresh Papers` запускает цепочку `collect -> score`, после чего новые статьи появляются в списке без ручного refresh.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/setup/review-dashboard.md docs/decisions/phase-12-dashboard-live-seed.md
git commit -m "docs: document dashboard live seed workflow"
```
