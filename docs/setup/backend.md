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

Проверка Phase GPU-3 от `2026-06-13`: `uv run pytest -q` завершился локально со статусом `16 passed in 1.82s`.

## Production command

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

## GPU-3 environment contract

Backend и worker читают следующие значения:

- `SCIENCE_PUB_LITELLM_URL=http://litellm:4000`
- `SCIENCE_PUB_LITELLM_MODEL=gpu/fast-small`
- `GPU_NODE_HOST=192.168.88.20`
- `GPU_LLM_FAST_URL=http://192.168.88.20:9000/v1`
- `GPU_LLM_DEEP_URL=http://192.168.88.20:9000/v1`
- `GPU_EMBEDDINGS_URL=http://192.168.88.20:9001/v1`

`SCIENCE_PUB_PROVIDER_DEFAULT` по-прежнему равен `mock`, поэтому Phase 09 scoring не переключен на реальный LLM inference по умолчанию.

## Readiness endpoints

- `GET /health` возвращает агрегированное состояние сервисов и внешних GPU upstream'ов.
- `GET /config-check` возвращает `valid=true/false`, детальные `checks` и runtime config.

Проверка на `scidocker` (`2026-06-13`) после `docker compose up -d --build`:

- `GET /health` -> `status=ok`
- `GET /config-check` -> `valid=true`
- `checks.litellm.ok=true`
- `checks.gpu_llm_fast.ok=true`
- `checks.gpu_llm_deep.ok=true`
- `checks.gpu_embeddings.ok=true`
