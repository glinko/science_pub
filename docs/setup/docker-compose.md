# Docker Compose Setup

## Файл

Стек описан в корневом `docker-compose.yml` и рассчитан на запуск из `/home/alex/science-pub`.

## Старт

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
python scripts/init_db.py
python scripts/test_stack.py
```

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

