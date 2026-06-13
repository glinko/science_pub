# GPU Node Environment Inventory

## Цель этапа

Phase GPU-0 выполнен как обследование processing node без изменений системы.
Целью было подтвердить фактическое состояние хоста `192.168.88.20`, проверить готовность GPU-окружения и зафиксировать расхождения между планом и реальным узлом.

## Идентификация узла

- Роль по факту: локальный GPU processing node
- Hostname: `llm`
- SSH-доступ: `alex@192.168.88.20`
- Дата обследования: `2026-06-13`

## Базовая платформа

- Форм-фактор: bare metal desktop, не VM с passthrough
- Hardware model: `MZ-B75-S`
- OS по факту: `Ubuntu 26.04 LTS`
- Kernel: `7.0.0-15-generic`
- Архитектура: `x86_64`

Вывод:
- Это расхождение с PDF-предположением `Ubuntu 24.04`.
- Для Phase GPU-1 и далее нужно учитывать, что команды установки и пакеты будут проверяться уже под `Ubuntu 26.04`, а не под `24.04`.

## GPU

- `nvidia-smi` работает
- Driver version: `595.71.05`
- CUDA version: `13.2`
- GPU: `NVIDIA GeForce RTX 3090`
- VRAM: `24576 MiB`

Состояние на момент обследования:
- GPU utilization: `0%`
- Температура: `43C`
- Память GPU занята примерно на `20.7 GiB` из `24 GiB`

Активные процессы на GPU:
- `llama-server` на порту `9000`, модель `qwen3.6-27b-q4_k_m.gguf`, потребление около `20008 MiB`
- `llama-server` на порту `9001`, embeddings `bge-m3-Q8_0.gguf`, потребление около `698 MiB`

Вывод:
- GPU уже сильно занят существующими inference-сервисами.
- Для будущих image/render/TTS задач понадобится дисциплина очередей и ограничения параллельности.
- Параллельный запуск тяжелой LLM и дополнительных GPU workload сейчас небезопасен.

## Docker и контейнерный стек

- `docker --version`: не установлен
- `docker compose version`: не установлен
- NVIDIA Container Toolkit: не найден
- Docker GPU runtime: не применим, потому что Docker отсутствует

Вывод:
- Узел не готов к `Phase GPU-1: NVIDIA Docker readiness`.
- Если мы хотим следовать PDF-архитектуре с `docker-compose.gpu.yml`, сначала придется установить Docker и только потом NVIDIA Container Toolkit.
- В текущем состоянии хост использует native/systemd запуск, а не Docker.

## Память и диск

- RAM: `30 GiB total`, `14 GiB used`, `14 GiB free`, `15 GiB available`
- Swap: `8 GiB`, используется умеренно
- Корневой диск: `/dev/sda2`
- Размер root FS: `937 GiB`
- Свободно на root: `827 GiB`
- Дополнительный mount: `/mnt/backup` около `1 TiB`

Вывод:
- По диску узел чувствует себя комфортно.
- Места достаточно и для моделей, и для кешей, и для временных артефактов рендера.

## Сеть

- Основной интерфейс: `enp3s0`
- IP: `192.168.88.20/24`
- Gateway: `192.168.88.1`
- Доступность по LAN: есть
- `ufw`: `inactive`

Слушающие TCP-порты:
- `22` — SSH
- `9000` — `llama-server` chat
- `9001` — `llama-server` embeddings
- `9100` — `agentmemory_openai_mux.py`
- `9002` — дополнительный python-сервис, требует отдельной идентификации в следующем этапе

Вывод:
- Узел сейчас не закрыт firewall-ом.
- Для production-like роли GPU worker это расходится с рекомендацией PDF: `LAN only` и allow only нужных портов.

## Уже работающие AI-сервисы

Запущенные user-level systemd units:
- `llama-qwen3.6.service`
- `llama-bge-m3.service`
- `agentmemory-openai-mux.service`

### llama-qwen3.6

- Runtime: native `llama-server`
- Binary: `/home/alex/src/llama-cpp-turboquant/build-cuda/bin/llama-server`
- Model path: `/opt/models/qwen3.6/qwen3.6-27b-q4_k_m.gguf`
- Port: `9000`
- Alias: `qwen3.6`
- Context: `131072`
- Endpoint health: `GET http://127.0.0.1:9000/health -> 200`
- Endpoint models: `GET http://127.0.0.1:9000/v1/models -> 200`

### llama-bge-m3

- Runtime: native `llama-server`
- Binary: `/usr/local/bin/llama-server`
- Model path: `/home/alex/models/bge-m3/bge-m3-Q8_0.gguf`
- Port: `9001`
- Alias: `bge-m3`
- Embeddings mode: enabled
- Endpoint health: `GET http://127.0.0.1:9001/health -> 200`
- Endpoint models: `GET http://127.0.0.1:9001/v1/models -> 200`

### AgentMemory mux

- Process: `/usr/bin/python3 /home/alex/.local/bin/agentmemory_openai_mux.py`
- Port: `9100`
- Health endpoint: `GET http://127.0.0.1:9100/health -> 200`

Вывод:
- На узле уже существует рабочий локальный LLM + embeddings baseline.
- Для Science Video Factory это можно использовать как стартовую опору вместо установки `llama.cpp` с нуля.
- Но нужно понять, разрешено ли нам переиспользовать текущие сервисы, или проект требует отдельную изоляцию под `science-video-factory`.

## Модели и директории

Найденные директории моделей:
- `/opt/models`
- `/home/alex/models`

Подтвержденные файлы моделей:
- `/opt/models/qwen3.6/qwen3.6-27b-q4_k_m.gguf`
- `/home/alex/models/bge-m3/bge-m3-Q8_0.gguf`

Дополнительные следы:
- `/home/alex/models/ideogram4-nf4`

Вывод:
- Единая storage policy пока не выровнена: часть моделей лежит в `/opt/models`, часть — в `/home/alex/models`.
- Перед `Phase GPU-2` нужно принять решение, нормализуем ли хранение в `/opt/models` или `/mnt/models`.

## Соответствие ожиданиям PDF

Что подтверждено:
- GPU host существует и доступен по SSH
- `nvidia-smi` работает
- RTX 3090 действительно доступна
- Есть LAN IP
- Есть место на диске
- Уже есть локальные LLM и embeddings endpoints

Что расходится с предположениями PDF:
- OS не `Ubuntu 24.04`, а `Ubuntu 26.04`
- Docker отсутствует
- NVIDIA Container Toolkit отсутствует
- Firewall не настроен
- Hostname не совпадает с предполагаемым `science-gpu-01`
- Узел уже используется для других локальных AI-сервисов

## Риски перед следующим этапом

- VRAM почти занята действующим `qwen3.6` сервисом, поэтому любые новые GPU workloads нужно вводить осторожно.
- Docker-first rollout по PDF нельзя начинать без отдельного шага установки Docker.
- Из-за уже работающих сервисов любое изменение портов, моделей или systemd units может задеть существующие use case на узле.
- Отсутствие `ufw` правил означает, что порты `9000`, `9001`, `9100`, `9002` сейчас открыты шире, чем хотелось бы для GPU worker роли.

## Рекомендация перед Phase GPU-1

Перед тем как переходить к Docker/NVIDIA toolkit или интеграции с `science-pub`, нужно отдельно подтвердить:

1. Переиспользуем ли существующие `llama-qwen3.6` и `bge-m3` сервисы для проекта.
2. Разрешено ли ставить Docker на этот узел, где уже есть native/systemd inference stack.
3. Нужно ли изолировать Science Video Factory в отдельные порты, каталоги и systemd units.
4. Нужна ли миграция model storage к единой схеме `/opt/models` или `/mnt/models`.
5. Нужно ли сначала включить `ufw` и ограничить доступ по LAN.

## Минимальный итог GPU-0

Phase GPU-0 можно считать завершенным:
- обследование хоста выполнено
- изменения системы не вносились
- критические расхождения с планом выявлены
- существующие локальные AI endpoints подтверждены живыми health-проверками
