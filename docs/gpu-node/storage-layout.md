# GPU Node Storage Layout

## Цель этапа

Phase GPU-2 выполняется для подготовки файловой структуры GPU processing node под `science-pub` без переноса уже работающих сервисов и без миграции существующих моделей.

Цель этапа:

- создать отдельный project root для новых GPU-компонентов проекта
- подготовить каталоги для данных, задач и выходных артефактов
- зафиксировать storage policy, чтобы следующие фазы не конфликтовали с уже работающим `llama`-стеком

## Принятые решения

На этом этапе зафиксированы такие defaults:

- project root: `/opt/science-video-factory`
- canonical root для новых моделей проекта: `/opt/models`
- отдельный `/mnt/models` пока не создаем
- существующие модели не переносим
- существующие native `llama` сервисы не трогаем

Почему так:

- `/opt/models` уже существует и используется текущим chat LLM
- `bge-m3` пока лежит в `/home/alex/models`, но его миграция сейчас была бы лишним риском
- `/opt/science-video-factory` позволяет отделить новые GPU-пайплайны проекта от уже живущей на машине AI-инфраструктуры

## Созданная структура

На узле должен быть подготовлен такой каркас:

```text
/opt/science-video-factory/
  docker-compose.gpu.yml
  .env.gpu.example
  data/
    cache/
    jobs/
    output/
  services/
    llama-cpp/
    embeddings/
    reranker/
    tts/
    comfyui/
    remotion/
  logs/
```

## Политика хранения

### 1. Project root

`/opt/science-video-factory` используется как operational root для новых GPU-сервисов `science-pub`.

Там будут жить:

- compose-файлы GPU-стека
- env-шаблоны
- runtime data
- output артефакты
- сервисные каталоги под дальнейшие фазы

### 2. Модели

Для новых моделей проекта canonical path считается таким:

```text
/opt/models/
```

Рекомендуемая целевая структура для следующих фаз:

```text
/opt/models/
  llm/
  embeddings/
  rerankers/
  tts/
  image/
```

Но на текущем этапе миграция не выполняется.

### 3. Legacy model paths

На момент выполнения Phase GPU-2 уже существуют legacy paths:

- `/opt/models/qwen3.6/qwen3.6-27b-q4_k_m.gguf`
- `/home/alex/models/bge-m3/bge-m3-Q8_0.gguf`
- `/home/alex/models/ideogram4-nf4`

Это означает:

- `qwen3.6` уже находится в preferred root `/opt/models`
- `bge-m3` и `ideogram4-nf4` пока остаются в legacy location `/home/alex/models`
- перенос этих директорий нужно делать отдельным контролируемым этапом, а не между делом в storage phase

### 4. Runtime data

Каталоги `data/` используются так:

- `data/cache` — временные кеши, распаковки, промежуточные данные
- `data/jobs` — job payloads, локальные метаданные, task artifacts
- `data/output` — итоговые локальные файлы до загрузки в MinIO или для дебага

### 5. Services

Каталоги `services/` на этом этапе являются scaffold-структурой под будущие фазы:

- `services/llama-cpp` — docker/native glue для LLM-профилей
- `services/embeddings` — конфиги и обвязка embeddings service
- `services/reranker` — future use
- `services/tts` — Piper или другой локальный TTS
- `services/comfyui` — workflow и service config
- `services/remotion` — render templates и service wiring

### 6. Outputs и MinIO

Локальный `data/output` не считается постоянным master storage.

Основная политика:

- GPU node генерирует локальный артефакт
- после успешной обработки результат выгружается в MinIO на main node
- локальная копия нужна для дебага, повторных прогонов и временного буфера

## Правила безопасности изменений

На этом этапе специально не делалось:

- не менялись порты `9000`, `9001`, `9100`
- не менялись user-level `systemd` units
- не переносились существующие модели
- не создавались symlink-миграции для model roots
- не включался firewall

Это важно, потому что узел уже используется как живой inference host.

## Что это значит для следующих фаз

### Phase GPU-3

При подъеме новых сервисов нужно решить:

- использовать ли существующий native `qwen3.6` как `deep-analysis`
- поднимать ли отдельный `fast-small` профиль рядом
- оставлять ли `bge-m3` в legacy path временно или переносить в `/opt/models/embeddings`

### Phase GPU-4 и дальше

Для новых моделей и сервисов лучше уже придерживаться единой схемы:

- новые assets и models складывать в `/opt/models/...`
- сервисный runtime хранить под `/opt/science-video-factory/...`

## Итог Phase GPU-2

Phase GPU-2 считается завершенным, если:

- создан `/opt/science-video-factory`
- создана структура `data/cache/jobs/output`
- созданы каталоги `services/*`
- подготовлены placeholder-файлы `docker-compose.gpu.yml` и `.env.gpu.example`
- storage policy зафиксирована в этой документации
