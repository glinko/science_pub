# Слой провайдеров

## LLM-провайдеры

- `MockLLMProvider` остается безопасным значением по умолчанию для milestone 1
- `LiteLLMProvider` отвечает за реальный HTTP-вызов в контейнер `litellm` на основном узле `192.168.88.150`
- backend не ходит к GPU endpoint напрямую: вся маршрутизация идет через LiteLLM alias layer

## Разделение ролей у LiteLLM-конфига

- `SCIENCE_PUB_LITELLM_MODEL` используется как общий default model для generic completion/readiness plumbing
- `SCIENCE_PUB_LITELLM_SCORING_MODEL` используется именно для scoring papers
- `SCIENCE_PUB_LITELLM_API_KEY` передается как `Authorization: Bearer ...`
- `SCIENCE_PUB_LITELLM_TIMEOUT_SECONDS` задает отдельный timeout для inference-path и не влияет на общий `request_timeout_seconds`

Это разделение оказалось практическим, а не декоративным: live scoring prompt на `gpu/deep-analysis` на стенде `scidocker` занял около `30.85s`, поэтому inference timeout пришлось развести с более короткими инфраструктурными запросами.

## LiteLLM aliases

- `gpu/fast-small` -> `qwen3.6` через `http://192.168.88.20:9000/v1`
- `gpu/deep-analysis` -> `qwen3.6` через `http://192.168.88.20:9000/v1`
- `gpu/embeddings` -> `bge-m3` через `http://192.168.88.20:9001/v1`

## Real scoring flow

При `provider=litellm` backend проходит следующие шаги:

1. `ScoringService` берет paper из БД
2. `LiteLLMPaperScorer` строит scoring prompt
3. `LiteLLMProvider` вызывает `/chat/completions` в `litellm`
4. parser извлекает JSON из plain JSON или fenced JSON ответа
5. validated `ScoreBreakdown` сохраняется в `paper_scores`
6. `paper.status` переводится в `scored`

## Поведение при ошибках

- если LiteLLM недоступен или истекает timeout, поднимается `ProviderNotReadyError`
- уже успешно обработанные papers не откатываются целиком: прогресс коммитится поштучно
- если модель вернула невалидный scoring payload для одной бумаги, paper помечается как `failed`, а batch продолжает работу

Это поведение нужно именно для controlled rollout: оно отделяет инфраструктурную недоступность провайдера от единичных проблем model output.

## Readiness и rollout warnings

- `/health` проверяет `database`, `redis`, `minio`, `qdrant`, `litellm`, `gpu_llm_fast`, `gpu_llm_deep`, `gpu_embeddings`
- `/config-check` по-прежнему может возвращать warnings `litellm_upstream_inference_not_configured` и `gpu_integrations_declared_but_not_wired`

Эти warnings не означают, что real scoring path не работает. Они означают, что rollout по умолчанию еще не переведен из `mock` в always-on режим.

## Queue

- `RQJobDispatcher` используется в production
- `InlineJobDispatcher` используется в тестах
- queue contract для `provider=litellm` теперь проверяется отдельными API-тестами, включая фактический `enqueue()` payload
