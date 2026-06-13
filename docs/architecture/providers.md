# Слой провайдеров

## LLM

- `MockLLMProvider` остается значением по умолчанию для scoring в milestone 1 и для Phase 09 все еще используется как `provider_default=mock`.
- `LiteLLMProvider` в этой фазе реализует HTTP plumbing к контейнеру `litellm` на основном узле `192.168.88.150` и участвует в readiness-пути.
- Контейнер `litellm` маршрутизирует запросы к GPU-ноде `192.168.88.20`, а бизнес-код backend не ходит к GPU endpoint'ам напрямую.

## LiteLLM aliases

- `gpu/fast-small` -> `qwen3.6` через `http://192.168.88.20:9000/v1`
- `gpu/deep-analysis` -> `qwen3.6` через `http://192.168.88.20:9000/v1`
- `gpu/embeddings` -> `bge-m3` через `http://192.168.88.20:9001/v1`

Текущая фаза валидирует интеграционный слой, поэтому `gpu/fast-small` и `gpu/deep-analysis` сознательно используют один и тот же upstream.

Важно: верификация `2026-06-13` подтвердила живой LiteLLM routing и прямой completion через LiteLLM с `Authorization` header. Отдельная auth-verified проверка backend-driven inference через `LiteLLMProvider` в эту фазу не входила.

## Readiness

- `/health` проверяет `database`, `redis`, `minio`, `qdrant`, `litellm`, `gpu_llm_fast`, `gpu_llm_deep`, `gpu_embeddings`.
- Если все проверки успешны, backend возвращает `status=ok`; при любой проблеме состояние становится `degraded`.
- `/config-check` возвращает `valid`, `checks`, предупреждения `litellm_upstream_inference_not_configured` и `gpu_integrations_declared_but_not_wired`, а также текущую конфигурацию `gpu_node_host` и `litellm_model`.

## Storage

- `StorageService` оборачивает MinIO client.

## Queue

- `RQJobDispatcher` — production.
- `InlineJobDispatcher` — тестовый режим.
