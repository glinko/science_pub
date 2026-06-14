# Review Dashboard

## Назначение

`review dashboard` — это отдельный frontend-слой для ручного editorial review статей в `science-pub`.

Он нужен, чтобы:

- видеть все собранные статьи в одном месте;
- фильтровать их по ключевым признакам;
- открывать выбранную статью в detail-панели;
- быстро принимать решение `Approve` или `Reject`.

## Архитектура

- frontend находится в каталоге `dashboard/`;
- приложение собирается через `Vite`;
- production-выдача идет через отдельный `nginx`-контейнер;
- UI обращается к backend через `/api/*`, который проксируется в `backend:8000`.

## Первый workflow

Текущая версия dashboard поддерживает:

- layout `Table + Detail`;
- фильтры `status`, `source`, `category`, `min_score`, `search`;
- список статей с title, status, source, published date, category и score;
- detail-панель выбранной статьи;
- действия `Approve -> approved` и `Reject -> rejected`.

## Локальная проверка

```bash
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
```

Если Docker доступен:

```bash
docker compose config
docker compose up -d --build
```

После старта compose dashboard должен открываться на:

```text
http://localhost:3000
```

## Ограничения milestone 1

В эту версию сознательно не входят:

- auth;
- bulk actions;
- редакторские комментарии;
- realtime updates;
- audit trail;
- kanban/board режим;
- inline editing summary/script.
