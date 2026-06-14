# Papers API

## Endpoints

- `GET /papers`
- `GET /papers/{id}`
- `PATCH /papers/{id}/status`

## Поддерживаемые фильтры

- `source`
- `category`
- `published_from`
- `published_to`
- `status`
- `min_score`
- `include_scores`
- `search`

## Пагинация

Используются параметры `limit` и `offset`.

## Search

Параметр `search` выполняет серверную фильтрацию по:

- `title`
- `source_id`

Пример:

```bash
curl "http://localhost:8000/papers?status=scored&search=quantum&include_scores=true"
```

## Review workflow

Dashboard использует три базовых endpoint'а:

- `GET /papers` — список и фильтры
- `GET /papers/{id}` — detail выбранной статьи
- `PATCH /papers/{id}/status` — ручное решение редактора

Для ручного review в milestone 1 используются переходы:

- `Approve -> approved`
- `Reject -> rejected`
