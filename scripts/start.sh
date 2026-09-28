#!/usr/bin/env bash
# Запуск DocDiff из портативного пакета (Python внутри). Ничего устанавливать не нужно:
#   ./start.sh            → http://<сервер>:8080
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$DIR/.env" ] || cp "$DIR/.env.example" "$DIR/.env"
set -a; . "$DIR/.env"; set +a
export PYTHONPATH="$DIR/lib:$DIR" PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
cd "$DIR"
exec "$DIR/python/bin/python3" -m app "$@"
