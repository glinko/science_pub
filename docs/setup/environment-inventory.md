# Environment Inventory

## Целевое окружение

- Платформа: Proxmox node `pve`
- VM: `sci_docker`
- Образ: `local:iso/ubuntu-24.04-server-cloudimg-amd64.img`
- Профиль: `4 vCPU`, `8 GiB RAM`, `60 GB SSD240G`
- Сеть: `vmbr0`, DHCP reservation в диапазоне `192.168.88.150-199`

## Сервисы milestone 1

- `postgres` — основная БД
- `redis` — очередь и брокер для RQ
- `minio` — локальное объектное хранилище
- `qdrant` — vector DB, пока только как готовый сервис
- `litellm` — LLM router, пока в режиме readiness
- `backend` — FastAPI API
- `worker` — RQ worker
- `n8n` — orchestration слой

## Политика доступа

- В LAN публикуются `8000`, `5678`, `9001`, `6333`, `4000`
- `postgres`, `redis`, MinIO S3 API опубликованы только на `127.0.0.1`
- Reverse proxy и внешний доступ в milestone 1 не добавляются

