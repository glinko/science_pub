# Phase 09 Decision

## Статус

Phase 09 переведен из состояния `deferred` в состояние controlled rollout ready по состоянию на `2026-06-13`.

Реальный scoring через LiteLLM теперь поддерживается end-to-end при явном `provider=litellm`, но значение по умолчанию сознательно не меняется:

- `SCIENCE_PUB_PROVIDER_DEFAULT=mock`
- production rollout остается управляемым, а не автоматическим

## Что вошло в решение

- `LiteLLMProvider` стал auth-aware и использует `SCIENCE_PUB_LITELLM_API_KEY`
- для real scoring выделена отдельная модель `SCIENCE_PUB_LITELLM_SCORING_MODEL=gpu/deep-analysis`
- для LiteLLM inference выделен отдельный timeout `SCIENCE_PUB_LITELLM_TIMEOUT_SECONDS=60`
- `ScoringService` использует `LiteLLMPaperScorer` при `provider=litellm`
- parser scoring-ответа принимает как чистый JSON, так и fenced JSON в стиле ```json ... ```
- невалидный model output больше не валит весь batch: paper помечается как `failed`, а обработка продолжается
- уже успешно scored papers больше не откатываются при mid-batch ошибке провайдера, потому что прогресс коммитится поштучно
- API и queue contract закреплены тестами для `/score/papers` и `/jobs/score-papers`

## Что сознательно не меняется

- default scoring остается mock-first
- warning-сообщения `/config-check` сохраняются, потому что rollout еще не переведен в режим default-on
- scoring по-прежнему опирается на prompt-plus-JSON contract без дополнительного retry orchestration и без автоматического fallback на другой LLM

## Почему timeout зафиксирован на 60 секундах

На живой проверке `2026-06-13` реальный scoring prompt длиной `965` символов для `gpu/deep-analysis` завершился примерно за `30.85s`.

Из этого следуют два вывода:

- общий `request_timeout_seconds=10` подходит для health/arXiv/plumbing, но не для реального scoring
- даже `30s` оказалось недостаточно без запаса, поэтому для LiteLLM scoring выбран отдельный runtime timeout `60s`

## Верификация

Локально:

- `cd backend && uv run pytest -q`
- результат: `30 passed in 3.63s`

На хосте `scidocker` (`192.168.88.150`) после пересборки `backend` и `worker`:

- `GET /health` -> `200`, `status=ok`
- `GET /version` -> `200`
- `GET /config-check` -> `200`, `valid=true`
- `POST /score/papers` с `{"limit":1,"status":"collected","provider":"litellm"}` -> `200`
- ответ scoring smoke: `{"processed":1,"threshold":7.0,"provider":"litellm"}`
- в `paper_scores` записан `model_used = gpu/deep-analysis`

Это подтверждает, что Phase 09 больше не является только infrastructure-readiness заметкой: реальный backend-driven LiteLLM scoring path работает на целевом стенде.
