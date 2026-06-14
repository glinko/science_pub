# Phase 11: review dashboard

## Контекст

После фаз `00-10` проект уже умел:

- собирать статьи;
- хранить их в `papers`;
- ставить score;
- фильтровать и обновлять статусы через backend API.

Следующим узким местом оказался ручной review. Нужна была рабочая поверхность, где оператор может быстро просматривать статьи и утверждать или отклонять их без прямой работы с API.

## Решение

Для milestone 1 review-слой реализуется как отдельное frontend-приложение внутри репозитория:

- каталог: `dashboard/`
- runtime: `React + Vite`
- production-выдача: отдельный `nginx`-сервис в `docker-compose.yml`

Backend остается единственным источником истины. Dashboard не хранит отдельное бизнес-состояние и использует существующие endpoint'ы:

- `GET /papers`
- `GET /papers/{id}`
- `PATCH /papers/{id}/status`

## Почему не server-rendered экран внутри backend

Отдельный frontend был выбран потому, что:

- UI не смешивается с FastAPI runtime;
- review-слой можно развивать независимо от backend;
- проще добавлять последующие сценарии review без шаблонов внутри Python-приложения;
- API уже существует и подходит как контракт между слоями.

## Layout и UX

Для первой версии выбран layout `Table + Detail`.

Это дает:

- быстрый просмотр списка;
- detail-панель без перехода на отдельный route;
- естественное место для approve/reject действий.

## Первичный scope

В milestone 1 dashboard покрывает:

- все статьи, а не отдельную `selected-only` очередь;
- фильтры `status`, `source`, `category`, `min_score`, `search`;
- detail-панель статьи;
- решения:
  - `Approve -> approved`
  - `Reject -> rejected`

## Осознанные ограничения

В фазу не включены:

- auth и роли;
- комментарии к решению;
- bulk actions;
- realtime collaboration;
- board / kanban представление;
- audit trail.
