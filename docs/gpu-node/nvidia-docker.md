# NVIDIA Docker Readiness

## Цель этапа

Phase GPU-1 выполнен для узла `192.168.88.20`.
Цель этапа: установить Docker Engine, Docker Compose plugin и NVIDIA Container Toolkit, затем подтвердить, что Docker-контейнеры видят RTX 3090 через `--gpus all`.

## Входные условия

До начала этапа на узле было подтверждено:

- OS: `Ubuntu 26.04 LTS`
- GPU: `NVIDIA GeForce RTX 3090`
- Driver: `595.71.05`
- `nvidia-smi` работал
- Docker отсутствовал
- NVIDIA Container Toolkit отсутствовал
- существующие `llama-server` сервисы уже были запущены через user-level `systemd`

Принятые решения:

- существующие локальные LLM/embeddings сервисы переиспользуем
- Docker разрешено установить
- сетевой доступ на этом этапе не ограничиваем

## Что было установлено

### Docker

Установлены пакеты из официального Docker apt repository:

- `docker-ce`
- `docker-ce-cli`
- `containerd.io`
- `docker-buildx-plugin`
- `docker-compose-plugin`
- `docker-ce-rootless-extras`

Фактические версии после установки:

- Docker Engine: `29.5.3`
- Docker Compose plugin: `v5.1.4`

### NVIDIA Container Toolkit

Установлены пакеты из официального NVIDIA repository:

- `nvidia-container-toolkit`
- `nvidia-container-toolkit-base`

Фактическая версия:

- `1.19.1-1`

## Конфигурация Docker runtime

Команда `nvidia-ctk runtime configure --runtime=docker` записала конфигурацию в `/etc/docker/daemon.json`.

Текущее содержимое:

```json
{
  "runtimes": {
    "nvidia": {
      "args": [],
      "path": "nvidia-container-runtime"
    }
  }
}
```

После этого Docker daemon был перезапущен.

Проверка `docker info` показала:

- `Runtimes: io.containerd.runc.v2 nvidia runc`
- `Default Runtime: runc`

Вывод:

- runtime `nvidia` зарегистрирован корректно
- default runtime специально не переключался на `nvidia`, чтобы не менять поведение всех контейнеров на хосте
- GPU будет включаться явно через `--gpus all`

## Проверки после установки

### Docker service

Проверено:

- `docker.service` активен
- `docker.socket` активен
- `alex` добавлен в группу `docker`

Новая SSH-сессия для `alex` уже видит Docker без `sudo`.

### GPU smoke test в контейнере

Проверочная команда:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Результат:

- контейнер успешно стартует
- внутри контейнера видна `NVIDIA GeForce RTX 3090`
- определяются driver `595.71.05` и CUDA `13.2`

Важно:

- `nvidia-smi` внутри контейнера показывает GPU и VRAM, но не отображает процессы хоста `llama-server`, что нормально для такого способа проверки
- на хосте после проверки существующие `llama-server` процессы продолжили работать штатно

### Существующие AI-сервисы после установки

Повторно подтверждено:

- `http://127.0.0.1:9000/health -> 200`
- `http://127.0.0.1:9001/health -> 200`
- `http://127.0.0.1:9100/health -> 200`

Вывод:

- установка Docker и toolkit не сломала уже работающий native inference stack

## Операционные замечания

### 1. Узел уже живой, не “чистый”

На момент установки узел уже выполнял постоянные AI-задачи:

- chat LLM на `9000`
- embeddings на `9001`
- gateway на `9100`

Значит, дальнейшие Docker-сервисы для `science-pub` нельзя проектировать так, будто узел пустой.

### 2. VRAM уже сильно занята

На хосте стабильно занято примерно `20.7 GiB / 24 GiB` видеопамяти.

Это означает:

- ComfyUI, TTS на GPU и render-нагрузку нужно запускать только с очередями и ограничением параллельности
- одновременный запуск новой тяжелой GPU-задачи вместе с текущим `qwen3.6` может упереться в VRAM

### 3. После установки apt сообщил о pending kernel upgrade

Система сообщила, что ожидаемый kernel теперь `7.0.0-22-generic`, а хост все еще работает на `7.0.0-15-generic`.

Это не заблокировало Docker/NVIDIA Container Toolkit на текущем этапе, но означает:

- при следующем удобном окне обслуживания стоит отдельно обсудить reboot
- делать это в рамках Phase GPU-1 я не стал, потому что этап должен был остаться минимально инвазивным и не останавливать существующие inference-сервисы

## Итог Phase GPU-1

Phase GPU-1 можно считать завершенным:

- Docker установлен
- Docker Compose plugin установлен
- NVIDIA Container Toolkit установлен
- runtime `nvidia` подключен к Docker
- `docker --gpus all` успешно видит RTX 3090
- существующие локальные AI endpoints после установки остались рабочими

## Что это открывает дальше

Теперь узел готов к следующим вариантам развития:

1. Dockerized GPU stack для отдельных сервисов `science-pub`
2. Смешанный режим: существующие `llama-server` остаются native, а новые GPU-сервисы идут в Docker
3. Переход к `Phase GPU-2`: структура каталогов, storage policy и будущий `docker-compose.gpu.yml`

На текущем этапе наиболее безопасный следующий шаг:

- не переносить существующие `llama` сервисы
- не менять их порты
- подготовить отдельную директорию проекта и storage layout
- проектировать новые сервисы так, чтобы они уважали уже занятую VRAM
