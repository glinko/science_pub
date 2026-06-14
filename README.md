# Science Pub

`science-pub` — локальная фабрика научно-популярного контента с приоритетом на собственную инфраструктуру, ручной review и поэтапное расширение pipeline.

## Milestone 1

Текущий milestone покрывает:

- provisioning выделенной VM `sci_docker` в Proxmox;
- Docker Compose стек с `postgres`, `redis`, `minio`, `qdrant`, `backend`, `worker`, `n8n`, `litellm`, `dashboard`;
- FastAPI backend с `health`, `version`, `config-check`, arXiv collector, papers API, scoring API, analyze-script job и job queue;
- отдельный review dashboard для ручного отбора статей с фильтрами, detail-панелью, действиями `Approve` / `Reject` и live-seed кнопкой `Fetch Fresh Papers`;
- документацию по фазам `00-13`.

## Структура

- `backend/` — FastAPI, SQLAlchemy, Alembic, worker.
- `dashboard/` — frontend review dashboard на `React + Vite`.
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

```bash
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
```

После запуска compose review dashboard доступен на `http://localhost:3000`.

В dashboard доступен live-seed сценарий:

- кнопка `Fetch Fresh Papers` создает job `collect-arxiv` с payload `{ "categories": [], "max_results": 100 }`;
- после успешного collect автоматически создается job `score-papers` с payload `{ "limit": 20, "status": "collected", "provider": "mock" }`;
- UI показывает этапы `Collecting`, `Scoring`, `Done` или `Failed`;
- после успеха список статей обновляется без ручного refresh.

В backend доступен analyze-script этап:

- `POST /jobs/analyze-script-papers` берет бумаги со статусом `scored`;
- mock-pass создает `paper_summaries`, `scripts` и `scene_json`;
- при `provider="litellm"` сервис пытается улучшить mock-черновик через LiteLLM, но при ошибке сохраняет mock-результат;
- успешная paper переводится в `scripted`, а ошибка одной paper не откатывает уже обработанный batch.

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
