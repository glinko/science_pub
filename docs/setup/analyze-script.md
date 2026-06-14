# Analyze Script Pipeline

## Назначение

`analyze-script` — это backend-этап, который превращает paper в первый review-ready контентный draft.

В текущем milestone он делает сразу несколько вещей:

- создает нормализованный русский слой для editorial review;
- сохраняет `RU Title`, `RU Abstract` и короткое `Summary`;
- генерирует черновой `ru`-сценарий;
- сохраняет минимальный `scene_json` для следующей media-фазы.

## API

Основной entrypoint:

```text
POST /jobs/analyze-script-papers
```

Поддерживаются два сценария:

### 1. Single-paper review flow

```json
{"paper_id":"<paper-id>","provider":"mock"}
```

Поведение по умолчанию:

- `limit = 1`
- `status = "scored"`
- `provider = "mock"`

Этот режим нужен для detail-панели dashboard, когда оператор запускает `Analyze Script` по одной выбранной статье.

### 2. Batch flow

```json
{"limit":10,"status":"scored","provider":"mock"}
```

Этот режим сохраняется для backend smoke и технических batch-запусков.

## Что сохраняется

Для успешной paper сервис создает:

- запись в `paper_summaries`:
  - `normalized_title_ru`
  - `normalized_abstract_ru`
  - `short_summary_ru`
  - `technical_summary`
  - `popular_summary`
  - `limitations`
  - `hype_risks`
- запись в `scripts`;
- `scene_json` в `scripts.scene_json`;
- переход `papers.status -> scripted`.

## Поведение провайдеров

Pipeline остается staged:

1. deterministic `mock` draft;
2. optional `litellm` enrichment поверх уже собранного draft.

Это дает два преимущества:

- pipeline не зависит целиком от внешнего inference;
- single-paper editorial flow остается рабочим даже при временных проблемах с LiteLLM.

Если LiteLLM недоступен или возвращает невалидный JSON:

- mock draft сохраняется;
- paper все равно может перейти в `scripted`;
- уже полученный review-ready слой не теряется.

Если ломается обязательный mock-pass для конкретной paper:

- paper получает `failed`;
- уже обработанные papers не откатываются;
- batch продолжает работу по оставшимся элементам.

## Локальная проверка

Targeted tests:

```bash
cd backend
uv run pytest tests/test_jobs.py tests/test_analyze_script.py tests/test_paper_detail_api.py -q
```

Полный backend suite:

```bash
cd backend
uv run pytest -q
```

## Smoke

Локальный single-paper smoke:

```bash
curl -X POST http://localhost:8000/jobs/analyze-script-papers ^
  -H "Content-Type: application/json" ^
  -d "{\"paper_id\":\"<paper-id>\",\"provider\":\"mock\"}"
```

Проверить detail:

```bash
curl http://localhost:8000/papers/<paper-id>
```

Ожидаемый результат:

- job создается со `status=queued`;
- после завершения paper переходит в `scripted`;
- detail payload содержит `review_draft` с русским review-ready слоем.

## Ограничения текущей версии

В фазу сознательно не входят:

- PDF extraction;
- retrieval через Qdrant;
- ручное редактирование generated summary/script;
- несколько вариантов сценария;
- TTS;
- image/video generation.
