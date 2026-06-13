# Backend Setup

## Технологический стек

- Python `3.12`
- `uv`
- FastAPI
- Async SQLAlchemy
- Alembic

## Локальная разработка

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

## Production command

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

