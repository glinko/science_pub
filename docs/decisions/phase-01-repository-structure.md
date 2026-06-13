# Phase 01 Decision

## Выбор структуры

- monorepo `science-pub`
- Python package name: `app` внутри `backend/`
- отдельные зоны `backend/`, `infra/`, `docs/`, `scripts/`, `workflows/`, `assets/`

## Почему

Такой layout даёт единый deployable root и оставляет место для дальнейших video-generation фаз.

