# Review Dashboard

## Назначение

`review dashboard` — это отдельный frontend-слой для ручного editorial review статей в `science-pub`.

Он нужен, чтобы:

- видеть статьи в одной очереди;
- фильтровать их по ключевым признакам;
- открывать выбранную paper в detail-панели;
- запускать `Analyze Script` по одной статье;
- принимать editorial-решение через `Approve` или `Reject`.

## Архитектура

- frontend находится в `dashboard/`;
- runtime — `React + Vite`;
- production-выдача идет через отдельный `nginx`-сервис;
- UI ходит в backend через `/api/*`.

Backend остается единственным источником истины. Dashboard не хранит отдельное бизнес-состояние и работает через:

- `GET /papers`
- `GET /papers/{id}`
- `PATCH /papers/{id}/status`
- `POST /jobs/analyze-script-papers`
- `GET /jobs`

## Detail workflow

Текущий detail-driven flow выглядит так:

1. оператор выбирает статью в таблице;
2. detail-панель показывает scoring, source metadata и original source block;
3. если review-ready слоя еще нет, UI показывает `Review Draft` empty state;
4. оператор запускает `Analyze Script`;
5. dashboard poll'ит `/api/jobs`;
6. после `succeeded` detail повторно запрашивается через `GET /papers/{id}`;
7. в detail появляется:
   - `RU Title`
   - `RU Abstract`
   - `Summary`
   - marker `Review Draft Ready`

Original source остается видимым как reference-блок.

## Review-ready state

После успешного analyze-script detail-панель читает статью в таком порядке:

1. review-ready русский слой;
2. scoring и статус;
3. original source;
4. editorial actions.

Именно это делает detail не просто paper-view, а рабочей editorial surface.

## Действия

### Analyze Script

- работает по одной выбранной paper;
- создает job `analyze-script-papers`;
- во время выполнения показывает inline status `Preparing Russian review draft...`;
- после завершения автоматически обновляет detail.

### Approve / Reject

- остаются в detail action row;
- используют `PATCH /papers/{id}/status`;
- в UI работают как следующий шаг после появления review-ready draft.

## Live Seed

Кнопка `Fetch Fresh Papers` остается отдельным workflow для наполнения очереди:

- создает `collect-arxiv`;
- после успеха создает `score-papers`;
- обновляет список статей без ручного refresh.

## Локальная проверка

```bash
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
```

Если стек поднят локально:

1. открыть [http://localhost:3000](http://localhost:3000);
2. выбрать paper в таблице;
3. нажать `Analyze Script`;
4. дождаться появления `Review Draft Ready`;
5. убедиться, что detail показывает `RU Title`, `RU Abstract` и `Summary`;
6. проверить, что `Approve` и `Reject` продолжают работать.

## Ограничения milestone 1

В эту версию сознательно не входят:

- auth;
- bulk actions;
- редакторские комментарии;
- realtime collaboration;
- kanban/board режим;
- inline editing generated summary/script.
