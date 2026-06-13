# Science Pub

`science-pub` — локальная фабрика научно-популярного контента с приоритетом на собственную инфраструктуру, ручной review и поэтапное расширение pipeline.

## Milestone 1

Текущий milestone покрывает:

- provisioning выделенной VM `sci_docker` в Proxmox;
- Docker Compose стек с `postgres`, `redis`, `minio`, `qdrant`, `backend`, `worker`, `n8n`, `litellm`;
- FastAPI backend с `health`, `version`, `config-check`, arXiv collector, papers API, scoring API и job queue;
- документацию по фазам `00-10`.

## Структура

- `backend/` — FastAPI, SQLAlchemy, Alembic, worker.
- `infra/` — provisioning VM, bootstrap хоста, Litellm config.
- `scripts/` — init и smoke-test команды.
- `docs/` — решения, setup notes и архитектура.
- `workflows/n8n/` — заметки для orchestration.

## Локальная разработка

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

## Удалённый деплой

1. Скопировать `.env.example` в `.env` и заполнить секреты.
2. Запустить `python infra/provision_sci_docker.py`.
3. Выполнить bootstrap через `infra/bootstrap_sci_docker.sh`.
4. Задеплоить репозиторий на VM и поднять стек:

```bash
docker compose up -d --build
python scripts/init_db.py
python scripts/test_stack.py
```

