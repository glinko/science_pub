# Science Pub

`science-pub` — локальная фабрика научно-популярного контента с опорой на собственную инфраструктуру, ручной editorial review и поэтапное развитие production pipeline.

## Milestone 1

Текущий milestone покрывает:

- отдельную VM `sci_docker` под стек проекта;
- Docker Compose стек с `postgres`, `redis`, `minio`, `qdrant`, `backend`, `worker`, `n8n`, `litellm` и `dashboard`;
- FastAPI backend с `health`, `version`, `config-check`, arXiv collector, papers API, scoring API, analyze-script job и очередью задач;
- review dashboard с таблицей статей, detail-панелью, live-seed действием `Fetch Fresh Papers` и editorial workflow;
- review-ready detail flow: кнопка `Analyze Script` теперь работает по одной выбранной статье и после успешного job показывает `RU Title`, `RU Abstract` и `Summary`.

## Структура

- `backend/` — FastAPI, SQLAlchemy, Alembic, worker и job-логика.
- `dashboard/` — review dashboard на `React + Vite`.
- `infra/` — provisioning и bootstrap для `sci_docker`.
- `scripts/` — init и smoke-команды.
- `docs/` — решения, setup notes и архитектурные заметки.
- `workflows/n8n/` — заготовки под orchestration.

## Локальная разработка

Backend:

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

Dashboard:

```bash
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
```

После запуска compose dashboard доступен на [http://localhost:3000](http://localhost:3000).

## Review-Ready Detail

В detail-панели dashboard редакторский flow теперь выглядит так:

1. оператор выбирает статью в таблице;
2. в detail-панели запускает `Analyze Script`;
3. backend создает single-paper job `analyze-script-papers`;
4. после завершения detail автоматически обновляется и показывает:
   - `RU Title`
   - `RU Abstract`
   - `Summary`
5. после появления review-ready слоя доступны `Approve` и `Reject`.

Оригинальные `title` и `abstract` не исчезают: они остаются в `Original Source` как reference-блок.

## Analyze Script

В backend analyze-script этап теперь поддерживает два режима:

- batch-режим по статусу `scored`;
- single-paper режим по `paper_id`.

Для single-paper запуска используется:

```text
POST /jobs/analyze-script-papers
```

Минимальный payload:

```json
{"paper_id":"<paper-id>","provider":"mock"}
```

В результате backend:

- создает `paper_summaries` с review-ready русским слоем;
- создает `scripts` и `scene_json`;
- переводит paper в `scripted`.

## Удаленный деплой

1. Скопировать `.env.example` в `.env` и заполнить секреты.
2. Выполнить provisioning VM через `infra/provision_sci_docker.py`.
3. Выполнить bootstrap через `infra/bootstrap_sci_docker.sh`.
4. Поднять стек:

```bash
docker compose up -d --build
python scripts/init_db.py
python scripts/test_stack.py
```
