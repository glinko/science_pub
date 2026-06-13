#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/alex/science-pub"

sudo apt-get update
sudo apt-get install -y ca-certificates curl git ufw
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker alex

sudo mkdir -p "${PROJECT_ROOT}"/{data/postgres,data/redis,data/minio,data/qdrant,data/n8n,data/litellm,backups}
sudo chown -R alex:alex "${PROJECT_ROOT}"

sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 5678/tcp
sudo ufw allow 9001/tcp
sudo ufw allow 6333/tcp
sudo ufw allow 4000/tcp
sudo ufw --force enable

docker --version
docker compose version
hostnamectl

