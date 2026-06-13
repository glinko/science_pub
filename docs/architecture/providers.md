# Provider Layer

## LLM

- `MockLLMProvider` — активен в milestone 1
- `LiteLLMProvider` — проверяется на liveliness, inference отложен до Phase 9

## Storage

- `StorageService` оборачивает MinIO client

## Queue

- `RQJobDispatcher` — production
- `InlineJobDispatcher` — тестовый режим

