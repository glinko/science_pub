# Phase 12: dashboard live seed

## Контекст

После фазы 11 в проекте уже был рабочий review dashboard, но наполнение свежими статьями все еще требовало отдельного ручного запуска collect и score jobs вне UI.

Следующим узким местом стала не новая editorial функциональность, а operational gap: оператору нужна была одна понятная точка входа, чтобы быстро получить новые статьи прямо из dashboard.

## Решение

Для первой версии live-seed orchestration выполняется во frontend dashboard, а не через новый backend endpoint.

Dashboard переиспользует уже существующие endpoints:

- `POST /jobs/collect-arxiv`
- `POST /jobs/score-papers`
- `GET /jobs`

Пользователь видит одну кнопку `Fetch Fresh Papers`, а UI сам выполняет цепочку:

1. создает collect job;
2. poll'ит jobs до `succeeded` или `failed`;
3. после успешного collect создает score job;
4. poll'ит jobs до завершения score;
5. после успеха обновляет список статей без ручного refresh.

## Почему не новый backend endpoint

Отдельный orchestration endpoint вроде `POST /jobs/refresh-papers` не был выбран, потому что:

- существующие job primitives уже покрывают нужный сценарий;
- дополнительный backend слой увеличил бы scope без обязательной пользы для milestone 1;
- требовался быстрый прикладной UX-улучшатель, а не новая orchestration-архитектура.

## Зафиксированные defaults

Live-seed кнопка сейчас использует фиксированные payload'ы:

- collect: `{ "categories": [], "max_results": 100 }`
- score: `{ "limit": 20, "status": "collected", "provider": "mock" }`

Это решение намеренно упрощает интерфейс и не превращает dashboard в advanced control panel.

## Ограничения первой версии

В фазу не включены:

- ручной выбор arXiv categories из UI;
- настройка `max_results` из UI;
- выбор scoring provider;
- realtime push через websockets или SSE;
- межпользовательская защита от параллельных запусков;
- chaining следующих этапов pipeline после scoring.

## Итог

Dashboard теперь является не только review-поверхностью, но и практической точкой входа для пополнения review очереди. Это усиливает ценность уже существующей job-инфраструктуры без роста backend complexity.
