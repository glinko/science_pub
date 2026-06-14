# Спецификация: review-ready detail panel с RU-нормализацией

## Контекст

Сейчас `science-pub` уже умеет:

- собирать и скорить статьи;
- показывать их в review dashboard;
- запускать `analyze-script` как backend job;
- переводить paper в `scripted`.

Но для редакторской оценки этого еще недостаточно. В текущем detail-view редактор видит в основном сырой paper-слой: оригинальные `title`, `abstract`, metadata и score. Для реального editorial review это неудобно, потому что:

- текст может быть на английском;
- формулировки еще не нормализованы для русского редактора;
- summary/script уже могут существовать в backend, но UI не показывает их как review-ready слой.

## Цель

Сделать detail-панель dashboard основной редакторской поверхностью для одной выбранной статьи, где после одного действия `Analyze Script` редактор видит уже подготовленный русский слой:

- нормализованный `title` на русском;
- нормализованный `abstract` на русском;
- короткое русское summary;
- status/сигнал, что статья теперь готова к редакторской оценке.

## Зафиксированное продуктовое решение

### 1. Точка входа

Выбран вариант `B`: `Analyze Script` располагается в detail-панели выбранной статьи, а не в header.

Это означает:

- запуск идет только для одной явно выбранной статьи;
- действие воспринимается как editorial decision, а не как batch automation;
- UI остается компактным и не превращается в control center для всей очереди.

### 2. Один пользовательский action

Для редактора остается одна понятная кнопка:

- `Analyze Script`

Внутри backend этот action запускает не только script generation, но и подготовку review-ready русского слоя.

Пользователь не должен отдельно думать про:

- перевод title;
- перевод abstract;
- нормализацию формулировок;
- создание summary;
- создание script.

Все это входит в один orchestration step.

### 3. Что должно быть готово до редакторской оценки

После успешного `Analyze Script` detail-панель должна показывать уже не raw paper в приоритете, а review-ready слой:

- `RU Title`
- `RU Abstract`
- `Короткое summary`

Именно этот набор является минимальным обязательным слоем для редакторской оценки.

Оригинальные поля paper при этом не исчезают полностью, но уходят на второй план как reference block.

### 4. Приоритет чтения в detail-панели

Новая detail-панель должна читать статью в таком порядке:

1. review-ready русский слой;
2. score / status / source metadata;
3. original source data как справка;
4. editorial actions.

Это важно, потому что цель detail-view теперь не просто “показать paper”, а “дать редактору готовый материал для решения”.

## Архитектурный подход

### Frontend

Dashboard не делает собственную текстовую нормализацию. Его роль:

- показать выбранную статью;
- запустить `Analyze Script` для нее;
- дождаться завершения job;
- перегрузить detail;
- переключить presentation с raw-view на review-ready view.

### Backend

Backend остается источником истины и отвечает за:

- RU-нормализацию title;
- RU-нормализацию abstract;
- генерацию короткого summary;
- script generation;
- сохранение результата в БД.

### Data contract

Для UI этого среза нужно считать, что после успешного analyze/script backend должен вернуть или сделать доступными через detail endpoint:

- русский нормализованный заголовок;
- русский нормализованный abstract;
- русское summary;
- информацию о происхождении результата (`model_used` / provider marker);
- status, отражающий, что paper готова к следующему review шагу.

Если текущий detail endpoint еще не содержит этот слой, он должен быть расширен, а не обойден отдельными фронтенд-хаками.

## UI-поведение

### До analyze-script

Если для выбранной статьи review-ready слой еще не существует:

- detail показывает raw metadata и current score;
- видна primary-кнопка `Analyze Script`;
- есть краткий hint, что после действия появится русский review-ready слой.

### Во время analyze-script

Во время выполнения:

- кнопка disabled;
- виден inline status `Analyzing...` или `Preparing Russian review draft...`;
- повторный запуск для той же статьи невозможен;
- `Approve` / `Reject` на это время тоже лучше блокировать, чтобы не создавать гонку смыслов.

### После успеха

После завершения:

- detail автоматически обновляется;
- сверху показывается review-ready русский слой;
- появляется признак успешной подготовки, например `Review Draft Ready`;
- `Approve` / `Reject` снова становятся доступными.

### После ошибки

Если analyze/script не удался:

- detail остается на текущем состоянии;
- показывается понятная inline ошибка;
- редактор может повторить запуск позже;
- UI не должен притворяться, что русский слой готов.

## Структура detail-панели

Рекомендуемая структура:

1. Заголовок статьи + status badge
2. Блок `Review Draft`
   - `RU Title`
   - `RU Abstract`
   - `Summary`
3. Блок `Scoring`
   - final score
   - explanation / model
4. Блок `Original Source`
   - original title
   - original abstract
   - source / source id / categories / authors
5. Action row
   - `Analyze Script`
   - `Approve`
   - `Reject`

Если review-ready слой еще не существует, блок `Review Draft` заменяется empty state с CTA на запуск analyze-script.

## Статусы и смысловые переходы

Для UI этого среза важно не добавлять лишнюю новую терминологию без пользы.

Вариант по умолчанию:

- backend по-прежнему может использовать существующий `scripted`;
- frontend трактует наличие RU review-ready слоя как `ready for editorial review`;
- отдельный новый enum status не обязателен, если то же самое можно надежно вывести из существующих данных.

Иначе говоря, сначала нужно пытаться переиспользовать уже имеющийся `scripted` + generated content, а не заводить новый status ради одного UI-state.

## Что входит в scope

- новая detail-driven кнопка `Analyze Script`;
- отображение loading / success / error состояний для одной статьи;
- review-ready RU block в detail-панели;
- показ original source как secondary reference;
- обновление API contract для detail endpoint при необходимости;
- tests на detail workflow;
- документация этого UX-среза.

## Что не входит в scope

- batch analyze из header;
- ручное редактирование summary/script;
- отдельная кнопка `Translate`;
- сложный reviewer workflow с комментариями;
- diff-view между original и normalized текстом;
- multi-step moderation;
- редактирование generated script из dashboard.

## Тестовая стратегия

Нужны проверки минимум на следующие сценарии:

- detail-панель для paper без review-ready слоя показывает CTA `Analyze Script`;
- клик по `Analyze Script` отправляет правильный request/job;
- во время выполнения кнопки disabled и виден status;
- после успеха detail перерисовывается с `RU Title`, `RU Abstract` и `Summary`;
- `Approve` / `Reject` остаются рабочими после появления review-ready слоя;
- при ошибке показывается inline error, а fake success не отображается;
- original source block остается доступным как reference.

## Почему это правильный следующий шаг

После Phase 13 backend уже умеет превращать paper в первый контентный draft, но редактор пока не чувствует эту ценность в UI. Новый detail-срез закрывает именно этот разрыв:

- превращает generated content в видимую редакторскую поверхность;
- делает review действительно русскоязычным и удобным;
- удерживает workflow точечным и осмысленным;
- не раздувает dashboard до тяжелого orchestration UI.

Это естественное продолжение уже готовых review dashboard и analyze-script pipeline: теперь между “paper scored” и “editor approved” появляется понятный, читаемый и практически usable review-ready слой.
