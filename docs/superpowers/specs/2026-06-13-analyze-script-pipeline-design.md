# Спецификация: auto analyze+script pipeline для `science-pub`

## Контекст

Текущий milestone 1 уже покрывает путь:

- `collect`
- `list`
- `score`
- `queue`

Phase 09 дополнительно довел реальный `provider=litellm` scoring path до controlled rollout на `scidocker` (`192.168.88.150`), но следующий отрезок pipeline пока остается пустым на уровне бизнес-логики:

- `selected`
- `analyzed`
- `scripted`

При этом схема данных уже содержит нужные таблицы:

- `paper_summaries`
- `scripts`

и статусы `selected`, `analyzed`, `scripted` уже существуют в enum `PaperStatus`.

## Цель следующего среза

Добавить backend-only pipeline, который берет автоматически подходящие `scored` papers и создает для них:

- summary-анализ бумаги;
- черновой `ru`-сценарий для короткого ролика;
- `scene_json` с минимальной разбивкой по сценам.

Этот срез должен работать через job queue, не требовать фронтенда и не требовать миграций схемы.

## Зафиксированные продуктовые решения

### 1. Источник для нового pipeline

Pipeline стартует автоматически от бумаг со статусом `scored`.

На этой фазе ручной отбор через `selected` не обязателен. Это означает, что новый job работает как автоматический post-score этап, но запускается отдельным endpoint'ом, а не скрыто изнутри `/score/papers`.

### 2. Что считается результатом

Одна успешная обработка бумаги должна сразу производить:

- запись в `paper_summaries`;
- запись в `scripts`;
- заполненный `scene_json`;
- переход `papers.status` в `scripted`.

Промежуточный статус `analyzed` на этой фазе не становится внешней пользовательской остановкой. Он может использоваться только как внутренний технический этап внутри сервиса, но итоговый observable result для первой версии — это готовый черновик сценария.

### 3. Формат сценария

Первая версия создает:

- один сценарий на русском языке;
- формат: короткий ролик на `60-90` секунд;
- одна запись `scripts` на paper;
- `scene_json` с минимальной структурой сцен, пригодной для следующего media-этапа.

### 4. Стратегия генерации

Новый pipeline использует staged generation:

1. deterministic `mock` pass;
2. optional `litellm` enrichment поверх уже созданного черновика.

Это решение принято осознанно:

- `mock` гарантирует, что pipeline не остается без результата;
- `litellm` улучшает содержимое, но не является единственной точкой успеха;
- тесты могут оставаться детерминированными;
- rollout остается безопасным даже при проблемах с inference.

### 5. Способ запуска

Первая версия запускается только через job queue endpoint.

Синхронный API для analyze/script на этой фазе не нужен. Также не нужен скрытый auto-trigger прямо из `/score/papers`: scoring и analyze/script остаются раздельными этапами orchestration.

## Рекомендованная архитектура

### Новый queue endpoint

Нужен новый endpoint:

- `POST /jobs/analyze-script-papers`

Payload должен быть минимальным и похожим на текущий scoring job contract:

- `limit`
- `status` по умолчанию `scored`
- при необходимости `provider` или режим enrichment

Endpoint создает DB-backed job record и отправляет задачу в существующий dispatcher.

### Worker flow

Нужен отдельный worker task, который:

1. берет батч papers со статусом `scored`;
2. для каждой бумаги создает mock summary + mock script + mock scene plan;
3. сохраняет результат как минимально рабочий черновик;
4. пытается улучшить этот черновик через `litellm`;
5. при успешном enrichment обновляет summary/script;
6. переводит paper в `scripted`.

## Поведение при ошибках

### Ошибка mock-pass

Если mock generation не удался, paper не должен переводиться в `scripted`.

Так как mock-pass является обязательным bootstrap-слоем, ошибка на этом этапе считается ошибкой обработки бумаги. Для первой версии допустимо помечать такую paper как `failed`.

### Ошибка LiteLLM enrichment

Если mock-pass уже успешен, а `litellm` enrichment не удался:

- уже созданный mock-черновик сохраняется;
- paper все равно может перейти в `scripted`, если обязательные поля summary/script уже созданы;
- весь job batch не должен откатываться;
- прогресс по ранее обработанным бумагам не должен теряться.

Это согласуется с поведением Phase 09, где partial progress уже сохраняется поштучно.

### Прозрачность происхождения результата

`model_used` должен позволять понять происхождение итогового контента:

- mock-only результат;
- enriched результат через `gpu/deep-analysis`.

Даже если в текущей схеме `paper_summaries` и `scripts` содержат только по одному `model_used`, итоговое значение должно отражать финальный источник содержимого после enrichment.

## Данные и формат результата

### `paper_summaries`

Для первой версии `paper_summaries` должны использоваться так:

- `technical_summary` — короткая техническая суть работы;
- `popular_summary` — человеческое объяснение для широкой аудитории;
- `limitations` — главные ограничения/оговорки;
- `hype_risks` — где легко преувеличить значение исследования.

### `scripts`

Для первой версии `scripts` должны использоваться так:

- `format = short-video`
- `language = ru`
- `script_text` — готовый черновой voiceover/script для ролика
- `scene_json` — JSON-структура сцен

### `scene_json`

Первая версия не должна пытаться описать production-grade storyboard. Достаточно минимальной предсказуемой структуры, например:

- номер сцены;
- краткая цель сцены;
- текст сцены или связанный фрагмент narration;
- rough visual cue.

Главное требование — структура должна быть детерминированной и пригодной для следующей media-фазы.

## Границы scope

### Что входит

- новый queue endpoint;
- новый worker task;
- сервис анализа и генерации чернового сценария;
- deterministic mock generation;
- optional litellm enrichment;
- запись в `paper_summaries` и `scripts`;
- обновление `papers.status`;
- automated tests;
- документация по новой фазе/срезу.

### Что не входит

- фронтенд для ручного review;
- ручная moderation UI;
- несколько вариантов сценария;
- TTS;
- image/video generation;
- YouTube publishing;
- chaining analyze/script автоматически из `/score/papers`;
- изменение БД-схемы, если текущих таблиц достаточно.

## Тестовая стратегия

Нужны тесты минимум на следующие сценарии:

- queue endpoint принимает `analyze-script-papers` job и правильно enqueue-ит payload;
- happy path: paper со статусом `scored` получает summary, script, scene_json и статус `scripted`;
- mock-only path работает без LiteLLM;
- LiteLLM enrichment обновляет уже созданный mock-черновик;
- failure в enrichment не откатывает mock result и не валит весь batch;
- failure в одной paper не откатывает уже обработанные papers;
- job lifecycle корректно отражается в `jobs`.

## Почему это следующий правильный шаг

Текущий pipeline уже умеет собирать и ранжировать бумаги, но еще не превращает их в контентный артефакт. Новый analyze+script срез закрывает именно этот разрыв:

- от `interesting paper` к `черновик контента`;
- без фронтенда;
- без media complexity;
- с максимальным переиспользованием уже готовых таблиц, worker-инфраструктуры и LiteLLM rollout.

Это делает следующий milestone маленьким, проверяемым и естественно продолжающим уже завершенный scoring pipeline.
