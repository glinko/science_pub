# arXiv Collector

## Назначение

`POST /collect/arxiv` получает свежие статьи из arXiv, фильтрует последние `24 часа` и сохраняет только metadata + `pdf_url`.

## Параметры

```json
{
  "categories": ["cs.AI", "quant-ph"],
  "max_results": 20
}
```

## Дедупликация

Уникальность гарантируется парой `(source, source_id)`.

