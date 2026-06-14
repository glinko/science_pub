# Backend Setup

## Технологический стек

- Python `3.12`
- `uv`
- FastAPI
- Async SQLAlchemy
- Alembic

## Локальная разработка

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

Проверка `2026-06-13`:

- `uv run pytest -q`
- результат: `30 passed in 3.63s`

## Production command

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

## Environment contract

Нужно различать два слоя переменных:

- operator-facing compose vars в `.env`
- фактические `SCIENCE_PUB_*` переменные, которые читает `AppSettings`

Ключевые LiteLLM переменные после Phase 09:

- `SCIENCE_PUB_LITELLM_URL=http://litellm:4000`
- `SCIENCE_PUB_LITELLM_API_KEY=science-pub-local-only`
- `SCIENCE_PUB_LITELLM_MODEL=gpu/fast-small`
- `SCIENCE_PUB_LITELLM_SCORING_MODEL=gpu/deep-analysis`
- `SCIENCE_PUB_LITELLM_TIMEOUT_SECONDS=60`
- `SCIENCE_PUB_REQUEST_TIMEOUT_SECONDS=10`
- `SCIENCE_PUB_PROVIDER_DEFAULT=mock`

Практический смысл:

- `SCIENCE_PUB_LITELLM_MODEL` нужен для generic completion/readiness plumbing
- `SCIENCE_PUB_LITELLM_SCORING_MODEL` нужен именно для scoring papers
- `SCIENCE_PUB_LITELLM_TIMEOUT_SECONDS` нужен именно для inference path
- `SCIENCE_PUB_REQUEST_TIMEOUT_SECONDS` остается короче и продолжает обслуживать более быстрые HTTP-path, например arXiv и health-related запросы

На живой проверке `2026-06-13` scoring prompt для `gpu/deep-analysis` занял около `30.85s`, поэтому `30s` оказалось недостаточно без запаса, а `60s` стало рабочим baseline.

## GPU-3 environment contract

Compose продолжает маппить GPU routing переменные так, чтобы контейнеры `backend` и `worker` видели:

- `SCIENCE_PUB_GPU_NODE_HOST=192.168.88.20`
- `SCIENCE_PUB_GPU_LLM_FAST_URL=http://192.168.88.20:9000/v1`
- `SCIENCE_PUB_GPU_LLM_DEEP_URL=http://192.168.88.20:9000/v1`
- `SCIENCE_PUB_GPU_EMBEDDINGS_URL=http://192.168.88.20:9001/v1`

`SCIENCE_PUB_PROVIDER_DEFAULT` по-прежнему равен `mock`, поэтому real LiteLLM scoring включается только явно через `provider=litellm`.

## Readiness endpoints

- `GET /health` возвращает агрегированное состояние сервисов и GPU upstream'ов
- `GET /config-check` возвращает `valid`, `checks`, warnings и runtime config
- `GET /version` возвращает имя приложения, версию и build metadata при наличии

Проверка на `scidocker` (`192.168.88.150`) после `docker compose up -d --build backend worker`:

- `GET /health` -> `200`, `status=ok`
- `GET /version` -> `200`
- `GET /config-check` -> `200`, `valid=true`
- `checks.litellm.ok=true`
- `checks.gpu_llm_fast.ok=true`
- `checks.gpu_llm_deep.ok=true`
- `checks.gpu_embeddings.ok=true`

## Real scoring smoke

Проверка `2026-06-13` на `scidocker`:

- в БД был добавлен fixture paper со статусом `collected`
- `POST /score/papers` с `provider=litellm` вернул `200`
- ответ API: `{"processed":1,"threshold":7.0,"provider":"litellm"}`
- в `paper_scores` появилась запись с `model_used = gpu/deep-analysis`
- fixture paper перешел в статус `scored`

Это и есть минимальное эксплуатационное подтверждение, что backend-driven real LiteLLM scoring path работает, хотя rollout по умолчанию все еще удерживается на `mock`.
