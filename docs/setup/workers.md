# Workers

## Очередь

- Redis хранит очередь `science-pub`
- RQ worker запускается через `python -m app.workers.runner`

## Поддерживаемые jobs

- `collect-arxiv`
- `score-papers`

## API

- `POST /jobs/collect-arxiv`
- `POST /jobs/score-papers`
- `GET /jobs`

