#!/usr/bin/env bash
# Быстрый локальный запуск для разработки: ./run.sh  → http://localhost:8080
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PY" -m venv .venv
  .venv/bin/pip install -q -r requirements-dev.txt
fi
[ -f .env ] && { set -a; . ./.env; set +a; }
exec .venv/bin/python -m app
