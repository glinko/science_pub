# Database Schema

## Основные таблицы

- `papers`
- `paper_scores`
- `paper_summaries`
- `scripts`
- `assets`
- `videos`
- `jobs`

## Ключевые решения

- UUID первичные ключи
- `raw_metadata_json` хранится в `papers`
- `authors`, `categories`, `scene_json`, `metadata_json`, `input_json`, `output_json` хранятся как JSON
- pipeline status хранится в `papers.status`

