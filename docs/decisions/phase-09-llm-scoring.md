# Phase 09 Decision

## Статус

Phase 09 осознанно остается отложенной даже после интеграции GPU-3.

## Что уже готово

- `litellm` поднимается в compose и маршрутизирует alias'ы `gpu/fast-small`, `gpu/deep-analysis`, `gpu/embeddings` на GPU-ноду `192.168.88.20`.
- Backend знает рабочий `LiteLLMProvider`.
- `/health` и `/config-check` отражают readiness LiteLLM и GPU upstream'ов.
- На проверке `2026-06-13` backend вернул `status=ok`, а `/config-check` вернул `valid=true`.

## Что сознательно не переключено

- `SCIENCE_PUB_PROVIDER_DEFAULT` по-прежнему равен `mock`.
- `ScoringService` продолжает использовать `mock:heuristic-v1` как поведение по умолчанию.
- Реальный inference для scoring, schema validation ответа модели и fallback strategy остаются следующим milestone.

## Причина решения

Phase GPU-3 закрывает интеграционный риск: сеть, alias routing, readiness и доступность GPU endpoint'ов. Это не означает автоматический переход scoring на LLM без отдельного продуктового и эксплуатационного решения.
