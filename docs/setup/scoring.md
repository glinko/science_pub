# Scoring Setup

## Endpoint

`POST /score/papers`

## Формула

```text
0.30 * public_interest +
0.20 * visual_potential +
0.20 * novelty +
0.15 * practical_relevance +
0.10 * mystery +
0.05 * credibility
```

## Режим milestone 1

- активный провайдер: `mock`
- `LiteLLM` помечен как readiness-only
- порог отбора: `7.0`

