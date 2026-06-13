# Docker Compose Setup

## Файл

Стек описан в корневом `docker-compose.yml` и рассчитан на запуск из `/home/alex/science-pub` на основном узле `scidocker` (`192.168.88.150`).

## Старт

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
python scripts/init_db.py
python scripts/test_stack.py
```

Локальная compose-проверка в этой сессии не выполнялась, потому что на рабочей машине отсутствует бинарь `docker` (`CommandNotFoundException`). Вместо этого использовалась удаленная проверка на Docker-узле.

## GPU-3 routing

- Оператор задает `GPU_*` значения в `.env`.
- `docker-compose.yml` маппит их в `SCIENCE_PUB_GPU_*` переменные контейнеров `backend` и `worker`.
- `AppSettings` внутри приложения читает именно `SCIENCE_PUB_*` переменные, потому что использует `env_prefix="SCIENCE_PUB_"`.
- `litellm` остается отдельным контейнером основного стека и монтирует `./infra/litellm/config.yaml`.
- LiteLLM проксирует:
  - `gpu/fast-small` -> `192.168.88.20:9000/v1`
  - `gpu/deep-analysis` -> `192.168.88.20:9000/v1`
  - `gpu/embeddings` -> `192.168.88.20:9001/v1`

## Volumes

- `./data/postgres`
- `./data/redis`
- `./data/minio`
- `./data/qdrant`
- `./data/n8n`
- `./data/litellm`

## Порты

- `8000` — backend
- `5678` — n8n
- `9001` — MinIO console
- `6333` — Qdrant
- `4000` — LiteLLM

## Проверка от 2026-06-13

На `alex@192.168.88.150:/home/alex/science-pub` были выполнены:

```bash
docker compose up -d --build
docker compose up -d --force-recreate litellm
docker compose ps
```

Фактический результат:

- `backend`, `worker`, `litellm`, `postgres`, `redis`, `minio`, `qdrant`, `n8n` перешли в `Up`, после завершения healthcheck'ов `backend` и `worker` стали `healthy`.
- Отдельный `--force-recreate litellm` понадобился потому, что deployment directory на узле содержала старый `infra/litellm/config.yaml`, и работающий контейнер нужно было перезапустить для подхвата новых alias'ов.
