# Review Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в `science-pub` отдельный review dashboard для просмотра всех статей, фильтрации, детального просмотра и ручных решений `Approve` / `Reject`.

**Architecture:** Dashboard живет как отдельное frontend-приложение в каталоге `dashboard/`, собирается в статический bundle и отдается отдельным compose-сервисом через `nginx`. Для связи с FastAPI UI использует существующие endpoints `GET /papers`, `GET /papers/{id}`, `PATCH /papers/{id}/status`, а compose-сервис проксирует `/api/*` в backend, чтобы не вводить CORS-настройки и не смешивать UI с backend runtime.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React, TypeScript, Vite, Vitest, React Testing Library, nginx, Docker Compose

---

## File Structure

- Create: `dashboard/package.json`
  - Node-зависимости, `dev`, `build`, `test` и `preview` scripts.
- Create: `dashboard/package-lock.json`
  - Зафиксированные версии npm-зависимостей.
- Create: `dashboard/tsconfig.json`
  - TypeScript-конфигурация для browser-кода.
- Create: `dashboard/vite.config.ts`
  - Vite-конфиг и тестовая среда `jsdom`.
- Create: `dashboard/index.html`
  - Единственная HTML-точка входа.
- Create: `dashboard/src/main.tsx`
  - Монтирование React-приложения.
- Create: `dashboard/src/App.tsx`
  - Корневая orchestration-логика dashboard.
- Create: `dashboard/src/styles.css`
  - Базовая layout- и component-стилизация `Table + Detail`.
- Create: `dashboard/src/lib/api.ts`
  - HTTP-запросы `listPapers`, `getPaper`, `updatePaperStatus`.
- Create: `dashboard/src/lib/types.ts`
  - Типы `Paper`, `PaperStatus`, `LatestScore`, `PaperListResponse`.
- Create: `dashboard/src/lib/filters.ts`
  - Сборка query string для filters/search.
- Create: `dashboard/src/components/FiltersBar.tsx`
  - Поля `status`, `source`, `category`, `min_score`, `search`.
- Create: `dashboard/src/components/PapersTable.tsx`
  - Таблица списка статей, row selection и states.
- Create: `dashboard/src/components/PaperDetail.tsx`
  - Детальная панель статьи и approve/reject actions.
- Create: `dashboard/src/components/StatusBadge.tsx`
  - Единый рендер статуса статьи.
- Create: `dashboard/src/App.test.tsx`
  - UI-контракты для загрузки списка, фильтров, detail и решений.
- Create: `dashboard/Dockerfile`
  - Multi-stage build: `npm ci` + `npm run build` + `nginx`.
- Create: `dashboard/nginx.conf`
  - Отдача static bundle и proxy `/api/` на `http://backend:8000/`.
- Create: `backend/tests/test_papers_api.py`
  - API-контракты для `search`, detail и статусов `approved` / `rejected`.
- Modify: `backend/app/api/papers.py`
  - Добавление query-параметра `search`.
- Modify: `backend/app/services/papers.py`
  - Серверная фильтрация по `title` и `source_id`.
- Modify: `.env.example`
  - Переменная `DASHBOARD_PORT`.
- Modify: `docker-compose.yml`
  - Новый сервис `dashboard`.
- Modify: `README.md`
  - Краткий старт dashboard и его URL.
- Modify: `docs/setup/docker-compose.md`
  - Описание нового compose-сервиса и его порта.
- Modify: `docs/setup/papers-api.md`
  - Документация `search` и review-сценария.
- Create: `docs/setup/review-dashboard.md`
  - Отдельная документация по UX, запуску и проверке dashboard.
- Create: `docs/decisions/phase-11-review-dashboard.md`
  - Зафиксированные архитектурные решения по review UI.

### Task 1: Добавить backend search и зафиксировать review API-контракт

**Files:**
- Modify: `backend/app/api/papers.py`
- Modify: `backend/app/services/papers.py`
- Create: `backend/tests/test_papers_api.py`

- [ ] **Step 1: Написать падающий API test для поиска по `title` и `source_id`**

```python
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.paper import Paper


@pytest.mark.asyncio
async def test_list_papers_supports_search_by_title_and_source_id(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                Paper(
                    source="arxiv",
                    source_id="2606.11111v1",
                    title="Quantum relay for clean energy forecasting",
                    abstract="match by title",
                    authors=["A. One"],
                    categories=["cs.AI"],
                    pdf_url="https://example.org/1.pdf",
                    published_at=datetime(2026, 6, 14, 10, 0, tzinfo=UTC),
                    raw_metadata_json={},
                ),
                Paper(
                    source="arxiv",
                    source_id="2606.22222v1",
                    title="Biology paper without the keyword",
                    abstract="match by source id",
                    authors=["B. Two"],
                    categories=["q-bio"],
                    pdf_url="https://example.org/2.pdf",
                    published_at=datetime(2026, 6, 14, 11, 0, tzinfo=UTC),
                    raw_metadata_json={},
                ),
            ]
        )
        await session.commit()

    title_response = await app_client.get("/papers", params={"search": "energy"})
    source_response = await app_client.get("/papers", params={"search": "2606.22222"})

    assert title_response.status_code == 200
    assert [item["source_id"] for item in title_response.json()["items"]] == ["2606.11111v1"]
    assert source_response.status_code == 200
    assert [item["title"] for item in source_response.json()["items"]] == [
        "Biology paper without the keyword"
    ]
```

- [ ] **Step 2: Написать падающий API test на статусы `approved` и `rejected`**

```python
@pytest.mark.asyncio
async def test_patch_paper_status_accepts_approved_and_rejected(
    app_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.33333v1",
            title="Review target paper",
            abstract="status change target",
            authors=["C. Three"],
            categories=["cs.AI"],
            pdf_url="https://example.org/3.pdf",
            published_at=datetime(2026, 6, 14, 12, 0, tzinfo=UTC),
            raw_metadata_json={},
        )
        session.add(paper)
        await session.commit()
        await session.refresh(paper)
        paper_id = str(paper.id)

    approved = await app_client.patch(f"/papers/{paper_id}/status", json={"status": "approved"})
    rejected = await app_client.patch(f"/papers/{paper_id}/status", json={"status": "rejected"})

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
```

- [ ] **Step 3: Запустить только новый API-контракт и увидеть red phase**

Run: `uv run pytest tests/test_papers_api.py -q`

Expected: `FAILED`, потому что `GET /papers` пока не принимает `search`, а файл с тестами только что добавлен.

- [ ] **Step 4: Реализовать минимальный backend search**

```python
@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    session: AsyncSession = Depends(get_session),
    paper_repository: PaperRepository = Depends(get_paper_repository),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    category: str | None = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    status: PaperStatus | None = None,
    min_score: float | None = None,
    include_scores: bool = False,
    search: str | None = None,
    sort_by: str = "published_at",
    sort_order: str = "desc",
) -> PaperListResponse:
    total, items = await paper_repository.list_papers(
        session,
        limit=limit,
        offset=offset,
        source=source,
        category=category,
        published_from=published_from,
        published_to=published_to,
        status=status,
        min_score=min_score,
        include_scores=include_scores,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
```

```python
from sqlalchemy import Select, func, or_, select

...
    async def list_papers(
        self,
        session: AsyncSession,
        *,
        limit: int,
        offset: int,
        source: str | None,
        category: str | None,
        published_from,
        published_to,
        status: PaperStatus | None,
        min_score: float | None,
        include_scores: bool,
        search: str | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[int, list[PaperResponse]]:
        ...
        if search:
            needle = f"%{search.strip().lower()}%"
            conditions.append(
                or_(
                    func.lower(Paper.title).like(needle),
                    func.lower(Paper.source_id).like(needle),
                )
            )
```

- [ ] **Step 5: Прогнать backend tests повторно**

Run: `uv run pytest tests/test_papers_api.py tests/test_api.py -q`

Expected: all tests pass, включая новый `search`-контракт и переходы статусов.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/papers.py backend/app/services/papers.py backend/tests/test_papers_api.py
git commit -m "feat: add paper search for review dashboard"
```

### Task 2: Скелет dashboard-приложения и compose-сервис

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/package-lock.json`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.tsx`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/styles.css`
- Create: `dashboard/src/lib/types.ts`
- Create: `dashboard/src/lib/api.ts`
- Create: `dashboard/src/App.test.tsx`
- Create: `dashboard/Dockerfile`
- Create: `dashboard/nginx.conf`
- Modify: `.env.example`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Написать падающий frontend test на базовый layout**

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import App from "./App";

describe("App", () => {
  it("renders review dashboard shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            total: 0,
            limit: 10,
            offset: 0,
            items: [],
          }),
          { status: 200 },
        ),
      ),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: /science pub review/i })).toBeInTheDocument();
    expect(await screen.findByText(/выберите статью/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Запустить frontend test и увидеть red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: command fails, потому что каталог `dashboard/` и npm toolchain еще не созданы.

- [ ] **Step 3: Создать минимальный frontend shell, типы и compose-service**

```json
{
  "name": "science-pub-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 3000",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.3"
  }
}
```

```tsx
import { useEffect, useState } from "react";

import { listPapers } from "./lib/api";
import type { Paper } from "./lib/types";
import "./styles.css";

export default function App() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void listPapers({ include_scores: true }).then((payload) => {
      setPapers(payload.items);
      setLoading(false);
    });
  }, []);

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <h1>Science Pub Review</h1>
      </header>
      <section className="dashboard__layout">
        <div className="dashboard__table">{loading ? "Загрузка..." : `${papers.length} статей`}</div>
        <aside className="dashboard__detail">Выберите статью для детального просмотра.</aside>
      </section>
    </main>
  );
}
```

```ts
export async function listPapers(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }

  const response = await fetch(`/api/papers?${query.toString()}`);
  if (!response.ok) {
    throw new Error("papers_list_failed");
  }
  return response.json();
}
```

```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
```

```nginx
server {
  listen 3000;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri /index.html;
  }

  location /api/ {
    proxy_pass http://backend:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

```yaml
  dashboard:
    build:
      context: ./dashboard
    container_name: science-pub-dashboard
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "${DASHBOARD_PORT}:3000"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:3000 >/dev/null"]
      interval: 15s
      timeout: 5s
      retries: 10
    networks: [science-pub]
```

```env
DASHBOARD_PORT=3000
```

- [ ] **Step 4: Установить npm-зависимости и прогнать новый frontend test**

Run: `npm --prefix dashboard install`

Run: `npm --prefix dashboard test -- --run`

Expected: базовый layout test passes.

- [ ] **Step 5: Проверить compose-конфиг**

Run: `docker compose config`

Expected: конфигурация валидна и содержит сервис `dashboard`.

- [ ] **Step 6: Commit**

```bash
git add .env.example docker-compose.yml dashboard
git commit -m "feat: scaffold review dashboard service"
```

### Task 3: Список, фильтры и состояния интерфейса

**Files:**
- Create: `dashboard/src/components/FiltersBar.tsx`
- Create: `dashboard/src/components/PapersTable.tsx`
- Create: `dashboard/src/components/StatusBadge.tsx`
- Create: `dashboard/src/lib/filters.ts`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/styles.css`
- Modify: `dashboard/src/App.test.tsx`

- [ ] **Step 1: Написать падающие frontend tests на filters, empty state и error state**

```tsx
it("sends search and status filters to the papers endpoint", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
    );
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await screen.findByRole("heading", { name: /science pub review/i });
  await userEvent.type(screen.getByLabelText(/search/i), "quantum");
  await userEvent.selectOptions(screen.getByLabelText(/status/i), "collected");

  await waitFor(() =>
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("/api/papers?"),
    ),
  );
  expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("search=quantum");
  expect(String(fetchMock.mock.calls.at(-1)?.[0])).toContain("status=collected");
});

it("renders empty state when filters return no papers", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), { status: 200 }),
    ),
  );

  render(<App />);

  expect(await screen.findByText(/ничего не найдено/i)).toBeInTheDocument();
});

it("renders backend error state", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));

  render(<App />);

  expect(await screen.findByText(/не удалось загрузить статьи/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Запустить frontend tests и увидеть red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: `FAILED`, потому что фильтры, empty state и error state еще не реализованы.

- [ ] **Step 3: Реализовать filter bar, query builder и table**

```ts
export type PaperFilters = {
  status: string;
  source: string;
  category: string;
  min_score: string;
  search: string;
};

export function buildPapersQuery(filters: PaperFilters) {
  const params = new URLSearchParams({
    include_scores: "true",
    limit: "25",
    offset: "0",
  });

  if (filters.status) params.set("status", filters.status);
  if (filters.source) params.set("source", filters.source);
  if (filters.category) params.set("category", filters.category);
  if (filters.min_score) params.set("min_score", filters.min_score);
  if (filters.search) params.set("search", filters.search);

  return params.toString();
}
```

```tsx
export function FiltersBar({
  filters,
  onChange,
}: {
  filters: PaperFilters;
  onChange: (next: PaperFilters) => void;
}) {
  return (
    <section className="filters">
      <label>
        Search
        <input
          aria-label="Search"
          value={filters.search}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
        />
      </label>
      <label>
        Status
        <select
          aria-label="Status"
          value={filters.status}
          onChange={(event) => onChange({ ...filters, status: event.target.value })}
        >
          <option value="">All</option>
          <option value="collected">Collected</option>
          <option value="scored">Scored</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
    </section>
  );
}
```

```tsx
if (error) {
  return <div className="state state--error">Не удалось загрузить статьи.</div>;
}

if (!loading && papers.length == 0) {
  return <div className="state state--empty">Ничего не найдено. Измените фильтры.</div>;
}
```

- [ ] **Step 4: Прогнать frontend tests повторно**

Run: `npm --prefix dashboard test -- --run`

Expected: filters, empty state и error state pass.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/App.tsx dashboard/src/App.test.tsx dashboard/src/styles.css dashboard/src/lib/filters.ts dashboard/src/components/FiltersBar.tsx dashboard/src/components/PapersTable.tsx dashboard/src/components/StatusBadge.tsx
git commit -m "feat: add review dashboard filters and list states"
```

### Task 4: Detail-панель и approve/reject workflow

**Files:**
- Create: `dashboard/src/components/PaperDetail.tsx`
- Modify: `dashboard/src/lib/api.ts`
- Modify: `dashboard/src/lib/types.ts`
- Modify: `dashboard/src/App.tsx`
- Modify: `dashboard/src/App.test.tsx`
- Modify: `dashboard/src/styles.css`

- [ ] **Step 1: Написать падающие frontend tests на row selection и approve/reject**

```tsx
it("opens selected paper in the detail panel", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/papers?")) {
        return new Response(
          JSON.stringify({
            total: 1,
            limit: 10,
            offset: 0,
            items: [
              {
                id: "11111111-1111-1111-1111-111111111111",
                source: "arxiv",
                source_id: "2606.55555v1",
                title: "Selected paper",
                abstract: "Detail abstract",
                authors: ["A. Reviewer"],
                categories: ["cs.AI"],
                pdf_url: "https://example.org/5.pdf",
                published_at: "2026-06-14T10:00:00Z",
                collected_at: "2026-06-14T10:05:00Z",
                status: "scored",
                raw_metadata_json: {},
                latest_score: {
                  final_score: 8.4,
                  explanation: "Strong fit",
                  model_used: "mock:heuristic-v1",
                  created_at: "2026-06-14T10:06:00Z"
                }
              }
            ]
          }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify({
          id: "11111111-1111-1111-1111-111111111111",
          source: "arxiv",
          source_id: "2606.55555v1",
          title: "Selected paper",
          abstract: "Detail abstract",
          authors: ["A. Reviewer"],
          categories: ["cs.AI"],
          pdf_url: "https://example.org/5.pdf",
          published_at: "2026-06-14T10:00:00Z",
          collected_at: "2026-06-14T10:05:00Z",
          status: "scored",
          raw_metadata_json: {},
          latest_score: {
            final_score: 8.4,
            explanation: "Strong fit",
            model_used: "mock:heuristic-v1",
            created_at: "2026-06-14T10:06:00Z"
          }
        }),
        { status: 200 },
      );
    }),
  );

  render(<App />);

  await userEvent.click(await screen.findByRole("button", { name: /selected paper/i }));

  expect(await screen.findByText(/detail abstract/i)).toBeInTheDocument();
  expect(screen.getByText(/mock:heuristic-v1/i)).toBeInTheDocument();
});

it("approves a paper and updates the visible status", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/papers?")) {
      return new Response(
        JSON.stringify({
          total: 1,
          limit: 10,
          offset: 0,
          items: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              source: "arxiv",
              source_id: "2606.55555v1",
              title: "Selected paper",
              abstract: "Detail abstract",
              authors: ["A. Reviewer"],
              categories: ["cs.AI"],
              pdf_url: "https://example.org/5.pdf",
              published_at: "2026-06-14T10:00:00Z",
              collected_at: "2026-06-14T10:05:00Z",
              status: "scored",
              raw_metadata_json: {},
              latest_score: null
            }
          ]
        }),
        { status: 200 },
      );
    }
    if (init?.method === "PATCH") {
      return new Response(
        JSON.stringify({
          id: "11111111-1111-1111-1111-111111111111",
          source: "arxiv",
          source_id: "2606.55555v1",
          title: "Selected paper",
          abstract: "Detail abstract",
          authors: ["A. Reviewer"],
          categories: ["cs.AI"],
          pdf_url: "https://example.org/5.pdf",
          published_at: "2026-06-14T10:00:00Z",
          collected_at: "2026-06-14T10:05:00Z",
          status: "approved",
          raw_metadata_json: {},
          latest_score: null
        }),
        { status: 200 },
      );
    }
    return new Response(
      JSON.stringify({
        id: "11111111-1111-1111-1111-111111111111",
        source: "arxiv",
        source_id: "2606.55555v1",
        title: "Selected paper",
        abstract: "Detail abstract",
        authors: ["A. Reviewer"],
        categories: ["cs.AI"],
        pdf_url: "https://example.org/5.pdf",
        published_at: "2026-06-14T10:00:00Z",
        collected_at: "2026-06-14T10:05:00Z",
        status: "scored",
        raw_metadata_json: {},
        latest_score: null
      }),
      { status: 200 },
    );
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await userEvent.click(await screen.findByRole("button", { name: /selected paper/i }));
  await userEvent.click(await screen.findByRole("button", { name: /approve/i }));

  expect(await screen.findByText(/approved/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Запустить frontend tests и увидеть red phase**

Run: `npm --prefix dashboard test -- --run`

Expected: `FAILED`, потому что detail panel и actions еще не подключены.

- [ ] **Step 3: Реализовать detail loading и status mutation**

```ts
export async function getPaper(paperId: string) {
  const response = await fetch(`/api/papers/${paperId}`);
  if (!response.ok) {
    throw new Error("paper_detail_failed");
  }
  return response.json();
}

export async function updatePaperStatus(paperId: string, status: "approved" | "rejected") {
  const response = await fetch(`/api/papers/${paperId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    throw new Error("paper_status_failed");
  }
  return response.json();
}
```

```tsx
export function PaperDetail({
  paper,
  busy,
  onApprove,
  onReject,
}: {
  paper: Paper | null;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!paper) {
    return <div className="detail detail--empty">Выберите статью для детального просмотра.</div>;
  }

  return (
    <section className="detail">
      <h2>{paper.title}</h2>
      <p>{paper.abstract}</p>
      <dl>
        <div><dt>Source</dt><dd>{paper.source}</dd></div>
        <div><dt>Source ID</dt><dd>{paper.source_id}</dd></div>
        <div><dt>Status</dt><dd>{paper.status}</dd></div>
        <div><dt>Score</dt><dd>{paper.latest_score?.final_score ?? "—"}</dd></div>
        <div><dt>Model</dt><dd>{paper.latest_score?.model_used ?? "—"}</dd></div>
      </dl>
      <div className="detail__actions">
        <button type="button" onClick={onApprove} disabled={busy}>Approve</button>
        <button type="button" onClick={onReject} disabled={busy}>Reject</button>
      </div>
    </section>
  );
}
```

```tsx
const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
const [mutating, setMutating] = useState(false);

useEffect(() => {
  if (!selectedPaperId) return;
  void getPaper(selectedPaperId).then(setSelectedPaper);
}, [selectedPaperId]);

async function handleDecision(nextStatus: "approved" | "rejected") {
  if (!selectedPaperId) return;
  setMutating(true);
  const updated = await updatePaperStatus(selectedPaperId, nextStatus);
  setSelectedPaper(updated);
  setPapers((current) => current.map((paper) => (paper.id === updated.id ? updated : paper)));
  setMutating(false);
}
```

- [ ] **Step 4: Прогнать frontend tests повторно**

Run: `npm --prefix dashboard test -- --run`

Expected: row selection, detail panel и approve path pass.

- [ ] **Step 5: Проверить production build**

Run: `npm --prefix dashboard run build`

Expected: `dist/` собирается без TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/App.tsx dashboard/src/App.test.tsx dashboard/src/styles.css dashboard/src/lib/api.ts dashboard/src/lib/types.ts dashboard/src/components/PaperDetail.tsx
git commit -m "feat: add review detail and approval workflow"
```

### Task 5: Документация и end-to-end verification

**Files:**
- Modify: `README.md`
- Modify: `docs/setup/docker-compose.md`
- Modify: `docs/setup/papers-api.md`
- Create: `docs/setup/review-dashboard.md`
- Create: `docs/decisions/phase-11-review-dashboard.md`

- [ ] **Step 1: Обновить документацию по dashboard и API**

```md
## Review Dashboard

Dashboard доступен отдельным сервисом на `http://localhost:3000` и использует backend API через внутренний proxy `/api`.

Основные сценарии:
- просмотр всех статей в layout `Table + Detail`;
- фильтры `status`, `source`, `category`, `min_score`, `search`;
- ручные действия `Approve -> approved` и `Reject -> rejected`.
```

```md
### GET /papers

Дополнительный query-параметр:

- `search`: серверный поиск по `title` и `source_id`

Пример:

`curl "http://localhost:8000/papers?status=scored&search=quantum&include_scores=true"`
```

- [ ] **Step 2: Прогнать полный backend и frontend test suite**

Run: `uv run pytest -q`

Run: `npm --prefix dashboard test -- --run`

Expected: все backend и frontend tests pass.

- [ ] **Step 3: Поднять локально весь stack и проверить health**

Run: `docker compose up -d --build`

Run: `docker compose ps`

Expected: `backend`, `worker`, `dashboard`, `postgres`, `redis`, `minio`, `qdrant`, `litellm`, `n8n` находятся в `running`/`healthy`.

- [ ] **Step 4: Выполнить smoke-проверки dashboard и backend**

Run: `curl http://localhost:8000/papers?limit=5&include_scores=true`

Run: `curl http://localhost:8000/papers?search=2606`

Run: `curl http://localhost:3000`

Expected:
- backend возвращает `200` для обычного списка и search;
- frontend HTML доступен на `:3000`;
- из браузера список открывается и approve/reject работают против реального backend.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/setup/docker-compose.md docs/setup/papers-api.md docs/setup/review-dashboard.md docs/decisions/phase-11-review-dashboard.md
git commit -m "docs: document review dashboard workflow"
```
