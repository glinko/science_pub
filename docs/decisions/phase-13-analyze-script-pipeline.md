# Phase 13: analyze script pipeline

## Контекст

После фаз review dashboard и live-seed проект уже умел:

- собирать бумаги;
- оценивать их;
- показывать оператору review-очередь;
- запускать queue-driven jobs.

Но pipeline все еще обрывался на уровне `interesting paper`, не создавая контентный draft. При этом схема данных уже содержала нужные таблицы `paper_summaries` и `scripts`, а статусы `analyzed` и `scripted` уже были готовы в enum.

## Решение

Для следующего среза выбран backend-only pipeline `analyze -> script` без новых миграций и без нового frontend.

Новая точка входа:

- `POST /jobs/analyze-script-papers`

Новый job берет бумаги со статусом `scored` и создает:

- запись в `paper_summaries`;
- запись в `scripts`;
- минимальный `scene_json`;
- переход бумаги в `scripted`.

## Почему выбран staged подход

Генерация устроена в два шага:

1. deterministic `mock` draft;
2. optional LiteLLM enrichment.

Это решение принято осознанно:

- pipeline не зависит целиком от внешнего inference;
- тесты остаются детерминированными;
- rollout можно проводить даже при нестабильном LiteLLM;
- появляется честный baseline, который уже производит usable draft.

## Поведение при ошибках

Если ломается enrichment:

- mock draft сохраняется;
- успешный результат не теряется;
- paper все равно может перейти в `scripted`.

Если ломается обязательный mock-pass для конкретной paper:

- paper получает статус `failed`;
- уже обработанные papers не откатываются;
- batch продолжает работу по оставшимся элементам.

Таким образом, новая фаза наследует partial-progress semantics, уже закрепленные для scoring и queue-инфраструктуры.

## Что сознательно не вошло

В этой фазе не добавляются:

- auto-trigger analyze/script из `/score/papers`;
- ручной UI для редактирования summary/script;
- множественные версии сценария;
- media generation;
- TTS;
- retrieval через Qdrant.

## Итог

Phase 13 переводит `science-pub` из состояния `papers with scores` в состояние `papers with first content draft`. Это естественный следующий шаг после review/dashboard слоя: теперь система умеет не только выбирать интересные бумаги, но и превращать их в первый пригодный для дальнейшего продакшна сценарный артефакт.
