# Phase GPU-3 Integration

## Цель

Подключить основной стек `science-pub` на `192.168.88.150` к уже работающим OpenAI-compatible endpoint'ам GPU-ноды `192.168.88.20` через LiteLLM, не перенося inference-сервисы GPU-ноды в compose основного стека.

## Итоговая схема

- `backend` и `worker` работают на `scidocker` (`192.168.88.150`).
- `litellm` работает на `scidocker` и использует `infra/litellm/config.yaml`.
- LiteLLM aliases:
  - `gpu/fast-small` -> `qwen3.6` -> `http://192.168.88.20:9000/v1`
  - `gpu/deep-analysis` -> `qwen3.6` -> `http://192.168.88.20:9000/v1`
  - `gpu/embeddings` -> `bge-m3` -> `http://192.168.88.20:9001/v1`

## Верификация от 2026-06-13

### Локально

```bash
cd backend
uv run pytest -q
```

Результат: `16 passed in 1.82s`.

Локальный `docker compose` не проверялся, потому что на рабочей машине отсутствует команда `docker`.

### На основном узле

Рабочая директория: `/home/alex/science-pub`

Перед удаленной проверкой deployment directory была синхронизирована с локальной реализацией Task 1-4 по минимальному набору runtime-файлов:

- `docker-compose.yml`
- `infra/litellm/config.yaml`
- `backend/app/config.py`
- `backend/app/providers/litellm_provider.py`
- `backend/app/providers/registry.py`
- `backend/app/services/health.py`
- `backend/app/api/health.py`
- `backend/app/schemas/health.py`
- `.env` был дополнен значениями `SCIENCE_PUB_LITELLM_MODEL=gpu/fast-small` и `GPU_*`

Причина синхронизации: удаленная копия не была Git checkout и содержала старый LiteLLM config с alias `local/qwen`.

Выполненные команды:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:4000/health/liveliness
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/config-check
docker compose up -d --force-recreate litellm
python3 - <<'PY'
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:4000/v1/chat/completions",
    data=json.dumps(
        {
            "model": "gpu/fast-small",
            "messages": [{"role": "user", "content": "Reply with exactly: GPU_OK"}],
        }
    ).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer science-pub-local-only",
    },
)
with urllib.request.urlopen(req, timeout=120) as resp:
    print(resp.status)
    print(resp.read().decode("utf-8"))
PY
```

Фактические результаты:

- `docker compose ps` после стабилизации показал `backend`, `worker`, `litellm`, `postgres`, `redis`, `minio`, `qdrant`, `n8n` в состоянии `Up`, а `backend` и `worker` — `healthy`.
- `GET /health/liveliness` вернул `"I'm alive!"`.
- `GET /health` вернул `status=ok`; все сервисы `database`, `redis`, `minio`, `qdrant`, `litellm`, `gpu_llm_fast`, `gpu_llm_deep`, `gpu_embeddings` вернули `ok=true`.
- `GET /config-check` вернул `valid=true`, `litellm_model=gpu/fast-small`, `gpu_node_host=192.168.88.20`.
- Реальный completion через `gpu/fast-small` вернул HTTP `200` и `choices[0].message.content="GPU_OK"`.

### На GPU-ноде

Выполненные команды:

```bash
curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1:9001/health
curl -fsS http://127.0.0.1:9000/v1/models
curl -fsS http://127.0.0.1:9001/v1/models
```

Фактические результаты:

- `9000 /health` -> `{"status":"ok"}`
- `9001 /health` -> `{"status":"ok"}`
- `9000 /v1/models` отдавал модель `qwen3.6`
- `9001 /v1/models` отдавал модель `bge-m3`

## Операционные замечания

- LiteLLM `master_key` обязателен для реальных `v1/chat/completions` запросов; без `Authorization: Bearer science-pub-local-only` сервис возвращал `401 Unauthorized`.
- После замены `infra/litellm/config.yaml` на `scidocker` потребовался `docker compose up -d --force-recreate litellm`, иначе контейнер продолжал обслуживать старый alias `local/qwen`.
