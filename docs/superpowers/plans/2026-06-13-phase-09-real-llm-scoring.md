# Phase 09 Real LLM Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести `science-pub` от mock-only scoring к первому управляемому real-LLM scoring path через LiteLLM, сохранив `mock` как безопасный default.

**Architecture:** Текущий GPU-3 уже доказал readiness, alias routing и живой LiteLLM proxy до GPU-ноды. В этой итерации мы не меняем инфраструктурную топологию, а добавляем два недостающих слоя: auth-aware `LiteLLMProvider` и детерминированный LLM scoring pipeline, который преобразует JSON-ответ модели в валидированный `ScoreBreakdown` и включается только при `provider=litellm`.

**Tech Stack:** FastAPI, Pydantic, httpx, SQLAlchemy, pytest, Docker Compose, LiteLLM

---

## File Structure

- Modify: `.env.example`
  - Добавляет явные переменные для auth и модели real scoring.
- Modify: `backend/app/config.py`
  - Расширяет settings для LiteLLM auth и выделенной scoring-модели.
- Modify: `backend/app/providers/litellm_provider.py`
  - Добавляет optional auth header и делает реальный клиент пригодным для защищенного LiteLLM.
- Modify: `backend/app/providers/registry.py`
  - Прокидывает новые settings в `LiteLLMProvider`.
- Modify: `backend/tests/test_settings.py`
  - Проверяет defaults для новых LiteLLM scoring settings.
- Modify: `backend/tests/test_litellm_provider.py`
  - Проверяет auth header и поведение клиента на защищенном proxy.
- Create: `backend/app/services/llm_scoring.py`
  - Изолирует prompt builder, JSON parsing и `LiteLLMPaperScorer`.
- Create: `backend/tests/test_llm_scoring.py`
  - Покрывает prompt contract и parser/validation для model output.
- Modify: `backend/app/services/scoring.py`
  - Переключает `provider=litellm` на реальный breakdown вместо mock fallback.
- Modify: `backend/tests/test_scoring.py`
  - Покрывает реальный scoring path, `model_used`, explanation и запись в `paper_scores`.
- Create: `backend/tests/test_score_api.py`
  - Проверяет `/score/papers` для `provider=litellm` и 503 path.
- Modify: `backend/tests/test_jobs.py`
  - Проверяет, что queue contract допускает `provider=litellm`.
- Modify: `docs/decisions/phase-09-llm-scoring.md`
  - Переводит решение из “deferred” в “controlled rollout ready”.
- Modify: `docs/architecture/providers.md`
  - Описывает auth-aware LiteLLMProvider и новый scoring flow.
- Modify: `docs/setup/backend.md`
  - Документирует `SCIENCE_PUB_LITELLM_API_KEY` и `SCIENCE_PUB_LITELLM_SCORING_MODEL`.

### Task 1: Зафиксировать auth и settings contract для LiteLLM scoring

**Files:**
- Modify: `.env.example`
- Modify: `backend/app/config.py`
- Modify: `backend/app/providers/litellm_provider.py`
- Modify: `backend/app/providers/registry.py`
- Modify: `backend/tests/test_settings.py`
- Modify: `backend/tests/test_litellm_provider.py`

- [ ] **Step 1: Написать падающий test на новые settings**

```python
def test_settings_expose_litellm_scoring_defaults() -> None:
    settings = AppSettings(
        database_url="sqlite+aiosqlite:///science.db",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        minio_access_key="key",
        minio_secret_key="secret",
        qdrant_url="http://localhost:6333",
        litellm_url="http://localhost:4000",
    )

    assert settings.litellm_api_key is None
    assert settings.litellm_scoring_model == "gpu/deep-analysis"
    assert settings.provider_default == "mock"
```

- [ ] **Step 2: Написать падающий provider test на auth header**

```python
@pytest.mark.asyncio
async def test_generate_sends_bearer_token_when_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            url: str,
            *,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> httpx.Response:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": {"content": "ok"}}]},
            )

    monkeypatch.setattr("app.providers.litellm_provider.httpx.AsyncClient", DummyClient)

    provider = LiteLLMProvider(
        base_url="http://localhost:4000",
        timeout=10.0,
        default_model="gpu/deep-analysis",
        api_key="science-pub-local-only",
    )

    result = await provider.generate("ping")

    assert result == "ok"
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer science-pub-local-only",
    }
```

- [ ] **Step 3: Запустить только settings/provider tests и увидеть red phase**

Run: `uv run pytest tests/test_settings.py tests/test_litellm_provider.py -q`

Expected: `FAILED`, потому что `litellm_api_key`, `litellm_scoring_model` и auth header пока не реализованы.

- [ ] **Step 4: Реализовать новые settings и auth-aware LiteLLMProvider**

```python
class AppSettings(BaseSettings):
    ...
    litellm_url: str
    litellm_model: str | None = None
    litellm_api_key: str | None = None
    litellm_scoring_model: str = "gpu/deep-analysis"
```

```python
class LiteLLMProvider:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        default_model: str | None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = default_model
        self.api_key = api_key

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
```

```python
response = await client.post(
    f"{self.base_url}/chat/completions",
    json=payload,
    headers=self._build_headers(),
)
```

```python
"litellm": LiteLLMProvider(
    base_url=settings.litellm_url,
    timeout=settings.request_timeout_seconds,
    default_model=settings.litellm_model,
    api_key=settings.litellm_api_key,
)
```

```env
SCIENCE_PUB_LITELLM_API_KEY=science-pub-local-only
SCIENCE_PUB_LITELLM_SCORING_MODEL=gpu/deep-analysis
```

- [ ] **Step 5: Прогнать tests повторно**

Run: `uv run pytest tests/test_settings.py tests/test_litellm_provider.py tests/test_registry.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .env.example backend/app/config.py backend/app/providers/litellm_provider.py backend/app/providers/registry.py backend/tests/test_settings.py backend/tests/test_litellm_provider.py
git commit -m "feat: add litellm auth settings for scoring"
```

### Task 2: Вынести prompt builder и parser для реального LLM scoring

**Files:**
- Create: `backend/app/services/llm_scoring.py`
- Create: `backend/tests/test_llm_scoring.py`

- [ ] **Step 1: Написать падающие tests для prompt и parser**

```python
from datetime import UTC, datetime

import pytest

from app.models.paper import Paper
from app.services.llm_scoring import build_scoring_prompt, parse_scoring_response


def test_build_scoring_prompt_mentions_all_score_dimensions() -> None:
    paper = Paper(
        source="arxiv",
        source_id="2606.12345v1",
        title="Quantum Shadows in Neural Space",
        abstract="A controllable paper abstract.",
        authors=["A. Researcher"],
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2606.12345v1",
        published_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        raw_metadata_json={"seed": "test"},
    )

    prompt = build_scoring_prompt(paper)

    assert "public_interest" in prompt
    assert "visual_potential" in prompt
    assert "Return valid JSON only" in prompt


def test_parse_scoring_response_returns_score_breakdown() -> None:
    breakdown = parse_scoring_response(
        \"\"\"{
          "public_interest": 8.4,
          "visual_potential": 7.9,
          "novelty": 8.1,
          "practical_relevance": 6.8,
          "mystery": 7.5,
          "credibility": 8.7,
          "explanation": "The topic is understandable, visual, and newsworthy."
        }\"\"\"
    )

    assert breakdown.public_interest == 8.4
    assert breakdown.credibility == 8.7


def test_parse_scoring_response_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        parse_scoring_response(
            '{"public_interest": 11, "visual_potential": 7, "novelty": 7, "practical_relevance": 7, "mystery": 7, "credibility": 7, "explanation": "bad"}'
        )
```

- [ ] **Step 2: Запустить parser tests и увидеть падение**

Run: `uv run pytest tests/test_llm_scoring.py -q`

Expected: `FAILED`, потому что `llm_scoring.py` пока не существует.

- [ ] **Step 3: Реализовать minimal prompt builder и JSON parser**

```python
import json

from app.models.paper import Paper
from app.schemas.scoring import ScoreBreakdown


def build_scoring_prompt(paper: Paper) -> str:
    return f"""
You are scoring a science paper for short-form science media.
Score each field from 0 to 10.
Return valid JSON only with keys:
public_interest, visual_potential, novelty, practical_relevance, mystery, credibility, explanation

Title: {paper.title}
Abstract: {paper.abstract}
Categories: {", ".join(paper.categories)}
Authors: {", ".join(paper.authors)}
""".strip()


def parse_scoring_response(raw_text: str) -> ScoreBreakdown:
    payload = json.loads(raw_text)
    return ScoreBreakdown.model_validate(payload)
```

```python
class LiteLLMPaperScorer:
    def __init__(self, provider: LiteLLMProvider, model: str) -> None:
        self.provider = provider
        self.model = model

    async def score_paper(self, paper: Paper) -> ScoreBreakdown:
        prompt = build_scoring_prompt(paper)
        raw_text = await self.provider.generate(prompt, model=self.model)
        return parse_scoring_response(raw_text)
```

- [ ] **Step 4: Прогнать llm scoring tests**

Run: `uv run pytest tests/test_llm_scoring.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm_scoring.py backend/tests/test_llm_scoring.py
git commit -m "feat: add llm scoring prompt and parser"
```

### Task 3: Переключить ScoringService на реальный breakdown при `provider=litellm`

**Files:**
- Modify: `backend/app/services/scoring.py`
- Modify: `backend/tests/test_scoring.py`

- [ ] **Step 1: Написать падающий service test для реального scoring path**

```python
@pytest.mark.asyncio
async def test_scoring_service_uses_litellm_breakdown_for_real_provider(
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.litellm_scoring_model = "gpu/deep-analysis"

    async with session_factory() as session:
        paper = Paper(
            source="arxiv",
            source_id="2606.00002v1",
            title="LLM scoring test paper",
            abstract="A paper inserted to validate litellm scoring.",
            authors=["Test Author"],
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2606.00002v1",
            published_at=datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
            raw_metadata_json={"seed": "llm"},
            status=PaperStatus.COLLECTED,
        )
        session.add(paper)
        await session.commit()

        async def fake_generate(prompt: str, model: str | None = None) -> str:
            assert model == "gpu/deep-analysis"
            return '''
            {
              "public_interest": 8.8,
              "visual_potential": 8.1,
              "novelty": 7.7,
              "practical_relevance": 7.2,
              "mystery": 7.6,
              "credibility": 8.9,
              "explanation": "Strong candidate for audience-facing coverage."
            }
            '''

        registry = ProviderRegistry(settings)
        monkeypatch.setattr(registry.get_llm_provider("litellm"), "generate", fake_generate)
        service = ScoringService(settings, PaperRepository(), registry)
        processed = await service.score_papers(
            session,
            limit=1,
            status=PaperStatus.COLLECTED,
            provider="litellm",
        )

        scores = list((await session.scalars(select(PaperScore).where(PaperScore.paper_id == paper.id))).all())

    assert processed == 1
    assert scores[0].model_used == "gpu/deep-analysis"
    assert scores[0].final_score > 0
```

- [ ] **Step 2: Запустить scoring tests и увидеть red phase**

Run: `uv run pytest tests/test_scoring.py -q`

Expected: `FAILED`, потому что `provider=litellm` пока все еще пишет mock breakdown и `model_used={provider}:deferred`.

- [ ] **Step 3: Реализовать реальный scoring flow**

```python
from .llm_scoring import LiteLLMPaperScorer


class ScoringService:
    ...
    async def score_papers(...):
        papers = await self.paper_repository.fetch_for_scoring(session, limit=limit, status=status)
        processed = 0
        for paper in papers:
            if provider == "mock":
                breakdown = self.mock_scorer.score_paper(paper)
                model_used = "mock:heuristic-v1"
            else:
                llm_provider = self.provider_registry.get_llm_provider(provider)
                llm_scorer = LiteLLMPaperScorer(
                    llm_provider,
                    self.settings.litellm_scoring_model,
                )
                breakdown = await llm_scorer.score_paper(paper)
                model_used = self.settings.litellm_scoring_model
```

- [ ] **Step 4: Прогнать scoring tests повторно**

Run: `uv run pytest tests/test_scoring.py -q`

Expected: all scoring tests pass, включая новый `provider=litellm` path.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: wire real litellm scoring path"
```

### Task 4: Закрепить API и queue contract для `provider=litellm`

**Files:**
- Create: `backend/tests/test_score_api.py`
- Modify: `backend/tests/test_jobs.py`
- Modify: `backend/app/api/score.py` (only if behavior needs tightening)

- [ ] **Step 1: Написать API tests на success и provider-not-ready**

```python
import pytest
from httpx import AsyncClient

from app.dependencies import get_scoring_service
from app.providers.litellm_provider import ProviderNotReadyError


@pytest.fixture()
def fake_scoring_service(app_client: AsyncClient) -> None:
    class FakeScoringService:
        async def score_papers(self, session, *, limit: int, status, provider: str) -> int:
            assert provider == "litellm"
            return 2

    app = app_client._transport.app
    app.dependency_overrides[get_scoring_service] = lambda: FakeScoringService()
    yield
    app.dependency_overrides.pop(get_scoring_service, None)


async def test_score_endpoint_accepts_litellm_provider(
    app_client: AsyncClient,
    fake_scoring_service: None,
) -> None:
    response = await app_client.post(
        "/score/papers",
        json={"limit": 2, "status": "collected", "provider": "litellm"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "litellm"
    assert response.json()["processed"] == 2


async def test_score_endpoint_returns_503_when_provider_is_not_ready(
    app_client: AsyncClient,
) -> None:
    class FailingScoringService:
        async def score_papers(self, session, *, limit: int, status, provider: str) -> int:
            raise ProviderNotReadyError("LiteLLM request failed: 401")

    app = app_client._transport.app
    app.dependency_overrides[get_scoring_service] = lambda: FailingScoringService()
    response = await app_client.post(
        "/score/papers",
        json={"limit": 1, "status": "collected", "provider": "litellm"},
    )
    app.dependency_overrides.pop(get_scoring_service, None)

    assert response.status_code == 503
```

- [ ] **Step 2: Расширить queue test**

```python
async def test_score_jobs_endpoint_accepts_litellm_provider(app_client: AsyncClient) -> None:
    response = await app_client.post(
        "/jobs/score-papers",
        json={"limit": 1, "status": "collected", "provider": "litellm"},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_type"] == "score-papers"
    assert payload["status"] == "queued"
```

- [ ] **Step 3: Запустить API/queue tests и увидеть red phase**

Run: `uv run pytest tests/test_score_api.py tests/test_jobs.py -q`

Expected: `FAILED`, потому что новый API test file еще не существует.

- [ ] **Step 4: Добавить minimal implementation if needed and re-run**

Run: `uv run pytest tests/test_score_api.py tests/test_jobs.py -q`

Expected: all tests pass; если `score.py` already returns 503 on `ProviderNotReadyError`, code changes may be unnecessary.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_score_api.py backend/tests/test_jobs.py backend/app/api/score.py
git commit -m "test: cover litellm scoring api contract"
```

### Task 5: Обновить docs и выполнить controlled remote verification

**Files:**
- Modify: `docs/decisions/phase-09-llm-scoring.md`
- Modify: `docs/architecture/providers.md`
- Modify: `docs/setup/backend.md`

- [ ] **Step 1: Обновить docs под новый статус scoring**

```md
## Phase 09: controlled real-LLM scoring

После GPU-3 backend по-прежнему оставляет `SCIENCE_PUB_PROVIDER_DEFAULT=mock`, но теперь поддерживает отдельный реальный путь для `provider=litellm`.

Важно:
- readiness и direct LiteLLM routing были подтверждены в GPU-3;
- в этой фазе backend начинает использовать auth-aware `LiteLLMProvider`;
- rollout остается controlled: default scoring не переключается автоматически.
```

- [ ] **Step 2: Прогнать полный backend suite локально**

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Подготовить remote `.env` и перезапустить нужные сервисы**

```bash
ssh alex@192.168.88.150 "cd /home/alex/science-pub && python3 - <<'PY'
from pathlib import Path
env_path = Path('.env')
lines = env_path.read_text(encoding='utf-8').splitlines()
wanted = {
    'SCIENCE_PUB_LITELLM_API_KEY': 'science-pub-local-only',
    'SCIENCE_PUB_LITELLM_SCORING_MODEL': 'gpu/deep-analysis',
    'SCIENCE_PUB_PROVIDER_DEFAULT': 'mock',
}
present = {line.split('=', 1)[0]: i for i, line in enumerate(lines) if '=' in line}
for key, value in wanted.items():
    if key in present:
        lines[present[key]] = f'{key}={value}'
    else:
        lines.append(f'{key}={value}')
env_path.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
PY
docker compose up -d --build backend worker litellm"
```

- [ ] **Step 4: Выполнить deterministic remote smoke для real scoring**

```bash
ssh alex@192.168.88.150 "cd /home/alex/science-pub && docker compose exec -T backend python - <<'PY'
import asyncio
from datetime import UTC, datetime
from app.config import get_settings
from app.db import build_session_manager
from app.enums import PaperStatus
from app.models.paper import Paper

async def main():
    settings = get_settings()
    sm = build_session_manager(settings)
    async with sm.factory() as session:
        paper = Paper(
            source='fixture',
            source_id='phase09-smoke-1',
            title='Smoke test paper for real llm scoring',
            abstract='A deterministic record for remote scoring verification.',
            authors=['Codex'],
            categories=['cs.AI'],
            pdf_url='https://example.invalid/paper.pdf',
            published_at=datetime.now(UTC),
            raw_metadata_json={'seed': 'phase09'},
            status=PaperStatus.COLLECTED,
        )
        session.add(paper)
        await session.commit()
    await sm.dispose()

asyncio.run(main())
PY
curl -fsS http://127.0.0.1:8000/score/papers -H 'Content-Type: application/json' -d '{\"limit\":1,\"status\":\"collected\",\"provider\":\"litellm\"}'"
```

Expected:
- HTTP `200`
- `provider=litellm`
- `processed` >= `1`

- [ ] **Step 5: Проверить записанный score и зафиксировать результат в docs**

```bash
ssh alex@192.168.88.150 "cd /home/alex/science-pub && docker compose exec -T postgres psql -U app -d science_video_factory -c \"select model_used, final_score, explanation from paper_scores order by created_at desc limit 1;\""
```

Expected:
- `model_used = gpu/deep-analysis`
- `final_score` not null
- `explanation` not empty

- [ ] **Step 6: Commit**

```bash
git add docs/decisions/phase-09-llm-scoring.md docs/architecture/providers.md docs/setup/backend.md
git commit -m "docs: record controlled real llm scoring rollout"
```
