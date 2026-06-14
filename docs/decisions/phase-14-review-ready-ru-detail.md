# Phase 14: review-ready RU detail

## Контекст

После Phase 13 проект уже умел:

- собирать и скорить статьи;
- показывать их в review dashboard;
- запускать queue-driven `analyze-script`;
- создавать summary и script draft в backend.

Но между `paper scored` и `editor approved` оставался важный разрыв. Редактор по-прежнему видел в detail-панели в первую очередь raw source layer:

- оригинальный `title`;
- оригинальный `abstract`;
- metadata и score.

Для реального editorial review этого было недостаточно. Нужен был слой, в котором текст уже нормализован и переведен на русский, а действие `Analyze Script` воспринимается как подготовка одной конкретной статьи к редакторской оценке.

## Решение

Для следующего шага выбран detail-driven workflow:

- `Analyze Script` живет в detail-панели выбранной paper;
- действие работает по одной статье, а не по batch header;
- backend после job сохраняет review-ready русский слой;
- detail endpoint возвращает вложенный `review_draft`;
- dashboard после завершения job автоматически перезагружает detail и показывает RU-слой как primary content.

`review_draft` фиксируется как detail-only контракт и содержит:

- `ru_title`
- `ru_abstract`
- `summary`
- `model_used`

List- и status-ответы не расширяются этим полем, чтобы не раздувать контракт без необходимости.

## Почему single-paper, а не batch action

Single-paper path выбран сознательно:

- editorial решение всегда привязано к конкретной статье;
- UI не превращается в orchestration control center;
- проще блокировать повторный запуск и отслеживать результат;
- detail-панель становится главной рабочей поверхностью редактора.

## Почему RU-слой строится в backend

Нормализация и перевод закреплены в backend, потому что:

- backend уже владеет summary/script generation;
- frontend не должен собирать review-ready текст из сырого source layer;
- один и тот же `review_draft` можно использовать и в dashboard, и в последующих automation-сценариях;
- источник истины остается в БД, а не в transient frontend state.

## Новая semantics detail-панели

После успешного `Analyze Script` detail читается в таком порядке:

1. review-ready русский слой;
2. score и статус;
3. original source как reference;
4. editorial actions.

Это меняет смысл detail-view: он больше не просто показывает paper, а дает редактору материал, уже подготовленный к решению.

## Поведение UI

Если `review_draft` еще нет:

- detail показывает empty state в секции `Review Draft`;
- видна кнопка `Analyze Script`;
- оператор понимает, что сначала нужно подготовить русскую review-ready версию.

Во время job:

- dashboard poll'ит `/api/jobs`;
- в detail виден inline status `Preparing Russian review draft...`;
- повторный запуск блокируется.

После успеха:

- detail повторно грузится через `GET /papers/{id}`;
- появляется `Review Draft Ready`;
- `RU Title`, `RU Abstract` и `Summary` становятся primary content;
- `Approve` и `Reject` остаются следующим editorial шагом.

## Что сознательно не добавлялось

В этой фазе не вводятся:

- новый enum status только ради UI;
- отдельная кнопка `Translate`;
- batch analyze из header;
- ручное редактирование generated draft;
- multi-step moderation и reviewer comments.

## Итог

Phase 14 закрывает разрыв между `analyze-script pipeline` и реальной редакторской работой. Теперь `science-pub` умеет не только сгенерировать backend draft, но и показать его оператору в usable detail surface с уже нормализованным русским слоем.
