# Phase 07 Decision

## LLM providers

- `mock` обязателен и остается fully working baseline для milestone 1.
- `litellm` больше не является только readiness-заглушкой: в Phase GPU-3 он стал рабочим integration layer между стеком на `192.168.88.150` и GPU-нодой `192.168.88.20`.

## Почему LiteLLM оставлен отдельным слоем

- Backend не знает о конкретной модели на GPU-ноде и работает только с alias'ами LiteLLM.
- Это позволяет менять upstream без правок в бизнес-коде.
- Для текущей фазы достаточно одного рабочего `qwen3.6` upstream для alias'ов `gpu/fast-small` и `gpu/deep-analysis`, пока мы валидируем сетевую и operational интеграцию.

## Зафиксированное поведение

- Liveness LiteLLM проверяется через `GET /health/liveliness`.
- Реальный completion проверяется прямым запросом к LiteLLM `POST /v1/chat/completions` с `Authorization: Bearer science-pub-local-only`.
- Проверка `2026-06-13` на `scidocker` подтвердила успешный ответ `200` от LiteLLM и completion с текстом `GPU_OK` через alias `gpu/fast-small`.
- Эта проверка не доказывает, что текущий `LiteLLMProvider` backend уже отправляет нужный auth header; в рамках Phase GPU-3 подтверждены readiness, alias routing и LiteLLM-direct inference.

## Почему registry остается

Registry по-прежнему упрощает переключение между `mock`, локальными alias'ами LiteLLM и будущими paid/local providers в следующих фазах.
