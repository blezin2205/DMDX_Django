#!/usr/bin/env bash
# Синхронізація проєкту на Raspberry Pi і перезапуск Docker.
# Запуск з Mac (потрібен робочий SSH: ключ або пароль у терміналі):
#   ./scripts/deploy-to-pi.sh
#   PI_PATH=~/DMDX_Django ./scripts/deploy-to-pi.sh

set -euo pipefail

PI_USER="${PI_USER:-blezin}"
PI_HOST="${PI_HOST:-192.168.0.112}"
PI_PATH="${PI_PATH:-Projects}"
SSH_TARGET="${PI_USER}@${PI_HOST}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${SSH_TARGET}:${PI_PATH}/"

echo "==> Sync ${ROOT} -> ${REMOTE}"
rsync -avz --delete \
  --exclude '.git/' \
  --exclude 'env/' \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'db.sqlite3' \
  --exclude 'staticfiles/' \
  --exclude 'media/' \
  --exclude '*.dump' \
  --exclude '.DS_Store' \
  "${ROOT}/" "${REMOTE}"

echo "==> Docker compose up --build on Pi (requirements_docker.txt + settings_docker.py)"
ssh "${SSH_TARGET}" "cd ${PI_PATH} && docker compose -f docker-compose.yml up --build -d"

echo "==> Done. App: http://${PI_HOST}:8000"
