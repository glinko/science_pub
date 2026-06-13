# MinIO Storage

## Buckets

- `papers`
- `assets`
- `audio`
- `videos`
- `thumbnails`

## Проверка

После `scripts/init_db.py` backend storage service должен:

1. создать отсутствующие buckets;
2. успешно выполнить write/read/delete smoke test.

