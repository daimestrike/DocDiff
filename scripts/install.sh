#!/usr/bin/env bash
# Установка DocDiff на сервере БЕЗ интернета. Запускается из распакованного пакета:
#   tar xzf docdiff-*.tar.gz && cd docdiff && sudo ./install.sh
# Тип пакета (portable / docker / venv) определяется автоматически.
# NO_SYSTEMD=1 — не ставить systemd-сервис, только подготовить и показать команду запуска.
set -euo pipefail
cd "$(dirname "$0")"
APP_DIR="$(pwd)"

[ -f .env ] || cp .env.example .env
set -a; . ./.env; set +a
PORT="${PORT:-8080}"

say() { printf '\033[1;32m>>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mОшибка:\033[0m %s\n' "$*" >&2; exit 1; }

wait_health() {
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 \
       || wget -qO- "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
      IP="$(hostname -I 2>/dev/null | awk '{print $1}')"; [ -n "$IP" ] || IP="$(hostname)"
      say "Сервис работает: http://${IP}:${PORT}/"
      return 0
    fi
    sleep 1
  done
  die "сервис не ответил на /health за 30 секунд — смотрите логи"
}

install_systemd() {  # $1 — команда запуска, $2 — команда для ручного запуска
  if [ "$(id -u)" = "0" ] && command -v systemctl >/dev/null && [ "${NO_SYSTEMD:-0}" != "1" ]; then
    id docdiff >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin docdiff
    chown -R docdiff:docdiff "$APP_DIR"
    sed -e "s|@APP_DIR@|$APP_DIR|g" -e "s|@EXEC@|$1|g" deploy/docdiff.service > /etc/systemd/system/docdiff.service
    systemctl daemon-reload
    systemctl enable docdiff >/dev/null 2>&1
    systemctl restart docdiff
    wait_health
    echo "Логи:       journalctl -u docdiff -f"
    echo "Перезапуск: systemctl restart docdiff"
    echo "Удаление:   systemctl disable --now docdiff && rm /etc/systemd/system/docdiff.service"
  else
    say "Готово (без systemd: нет root или NO_SYSTEMD=1). Запуск вручную:"
    echo "  $2"
  fi
}

# ------------------------------------------------------------------ portable: Python внутри
if [ -x python/bin/python3 ]; then
  python/bin/python3 -c "import sys; sys.path[:0]=['lib','.']; import app.main" \
    || die "встроенный Python не запустился (не та архитектура? uname -m = $(uname -m))"
  say "Портативный пакет проверен"
  install_systemd "$APP_DIR/start.sh" "$APP_DIR/start.sh"
  exit 0
fi

# ------------------------------------------------------------------ Docker
if [ -f docdiff-image.tar.gz ]; then
  command -v docker >/dev/null || die "docker не найден. Возьмите портативный пакет docdiff-*-linux-*.tar.gz"
  if docker compose version >/dev/null 2>&1; then DC="docker compose"
  elif command -v docker-compose >/dev/null; then DC="docker-compose"
  else die "не найден docker compose / docker-compose"; fi
  say "Загрузка образа"
  docker load -i docdiff-image.tar.gz
  say "Запуск контейнера"
  $DC up -d
  wait_health
  echo "Логи:       $DC logs -f        (в каталоге $APP_DIR)"
  echo "Остановка:  $DC down"
  exit 0
fi

# ------------------------------------------------------------------ venv: системный Python
[ -d wheels ] || die "непонятный пакет: нет ни python/, ни docdiff-image.tar.gz, ни wheels/"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || die "не найден $PY. Укажите: PYTHON=/usr/bin/python3.11 ./install.sh"
HAVE="$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
WANT="$(cat wheels/PYTHON_VERSION 2>/dev/null || echo "$HAVE")"
[ "$HAVE" = "$WANT" ] || die "пакет собран под Python $WANT, а на сервере $PY = $HAVE.
  Возьмите портативный пакет или пересоберите: PY_VERSION=$HAVE scripts/build_bundle.sh venv"

say "Создание виртуального окружения (Python $HAVE)"
rm -rf .venv
if ! "$PY" -m venv .venv 2>/dev/null; then
  # Debian/Ubuntu без пакета python3-venv: создаём без pip и ставим pip из колеса
  rm -rf .venv
  "$PY" -m venv --without-pip .venv || die "не удалось создать venv"
  PIP_WHL="$(ls wheels/pip-*.whl | head -1)"
  .venv/bin/python "$PIP_WHL/pip" install -q --no-index "$PIP_WHL"
fi
say "Установка зависимостей из wheels/ (без интернета)"
.venv/bin/python -m pip install -q --no-index --find-links wheels -r requirements.txt
install_systemd "$APP_DIR/.venv/bin/python -m app" \
  "cd $APP_DIR && set -a && . ./.env && set +a && .venv/bin/python -m app"
