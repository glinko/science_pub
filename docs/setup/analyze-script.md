# Analyze Script Pipeline

## Назначение

`analyze-script` — это backend-only этап, который превращает paper со статусом `scored` в первый контентный артефакт:

- summary-анализ статьи;
- черновой `ru`-сценарий для короткого ролика;
- минимальный `scene_json` для следующей media-фазы.

На этом этапе отдельный frontend не требуется. Запуск идет через job queue.

## API

Новый endpoint:

```text
POST /jobs/analyze-script-papers
```

Payload по умолчанию:

```json
{"limit":10,"status":"scored","provider":"mock"}
```

Поддерживаемые поля:

- `limit` — сколько бумаг брать за один запуск;
- `status` — исходный статус выборки, по умолчанию `scored`;
- `provider` — `mock` или `litellm`.

## Поведение

Сервис работает в два слоя:

1. deterministic `mock` pass;
2. optional `litellm` enrichment поверх уже собранного draft.

Итог для успешной paper:

- новая запись в `paper_summaries`;
- новая запись в `scripts`;
- `scene_json` в `scripts.scene_json`;
- переход `papers.status` в `scripted`.

Если LiteLLM недоступен или вернул плохой JSON:

- mock draft сохраняется;
- paper все равно может стать `scripted`;
- весь batch не откатывается.

Если ошибка произошла на обязательном mock-этапе для конкретной paper:

- эта paper получает статус `failed`;
- уже завершенные papers остаются сохраненными;
- batch продолжает работу по остальным бумагам.

## Локальная проверка

Запустить связанные tests:

```bash
cd backend
uv run pytest tests/test_jobs.py tests/test_analyze_script.py -q
```

Полный backend suite:

```bash
cd backend
uv run pytest -q
```

## Smoke

Если стек уже поднят локально:

```bash
curl -X POST http://localhost:8000/jobs/analyze-script-papers ^
  -H "Content-Type: application/json" ^
  -d "{\"limit\":1,\"status\":\"scored\",\"provider\":\"mock\"}"
```

Проверить jobs:

```bash
curl http://localhost:8000/jobs
```

Ожидаемый результат:

- новый job `analyze-script-papers` появляется в очереди;
- после завершения job имеет `status=succeeded`;
- соответствующая paper в БД переходит в `scripted`.

## Smoke на `sci-docker`

```bash
ssh alex@192.168.88.150 "cd /home/alex/science-pub && docker compose up -d --build backend worker"
ssh alex@192.168.88.150 "curl -fsS -X POST http://127.0.0.1:8000/jobs/analyze-script-papers -H 'Content-Type: application/json' -d '{\"limit\":1,\"status\":\"scored\",\"provider\":\"mock\"}'"
ssh alex@192.168.88.150 "curl -fsS http://127.0.0.1:8000/jobs"
```

## Ограничения текущей версии

В эту фазу сознательно не входят:

- PDF extraction;
- retrieval через Qdrant;
- несколько вариантов сценария;
- TTS;
- image/video generation;
- auto-trigger analyze/script прямо из `/score/papers`;
- editorial UI для редактирования generated summary/script.
