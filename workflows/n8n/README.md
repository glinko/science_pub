# n8n Workflow Notes

На milestone 1 `n8n` поднимается как готовый orchestration слой, но production workflow ещё не зафиксирован.

План следующего шага:

1. `Daily trigger`
2. `POST /collect/arxiv`
3. `POST /score/papers`
4. `GET /papers?include_scores=true`
5. Отправка daily summary в выбранный канал

