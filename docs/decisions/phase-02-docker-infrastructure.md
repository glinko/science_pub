# Phase 02 Decision

## Сервисы

- `postgres`
- `redis`
- `minio`
- `qdrant`
- `backend`
- `worker`
- `n8n`
- `litellm`

## Почему single compose

Один `docker-compose.yml` проще для первого milestone и лучше соответствует целевому smoke test.

## Секреты

Все секреты приходят из `.env`. Хардкод в compose не допускается.

