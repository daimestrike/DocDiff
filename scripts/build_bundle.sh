#!/usr/bin/env bash
# Сборка офлайн-пакета для сервера без интернета. Запускать на машине С интернетом
# (или в GitHub Actions — см. .github/workflows/release.yml).
#
#   scripts/build_bundle.sh portable  # Python + зависимости внутри архива, ничего ставить не нужно
#   scripts/build_bundle.sh docker    # образ Docker + compose   (нужен docker)
#   scripts/build_bundle.sh venv      # колёса под системный Python сервера + systemd
#
# Переменные:
#   ARCH=x86_64              архитектура сервера: x86_64 | aarch64 (portable, venv)
#   PLATFORM=linux/amd64     платформа образа, linux/arm64 для ARM (docker)
#   WITH_LIBREOFFICE=0|1     включить LibreOffice в образ (docker)
#   PY_VERSION=3.11          версия Python НА СЕРВЕРЕ (venv)
#   PIP_PLATFORMS="..."      переопределить платформы pip вручную
#   PBS_TAG, PBS_PY          релиз и версия python-build-standalone (portable)
#   PORTABLE_TRIPLE          целевая платформа Python (portable), по умолчанию ${ARCH}-unknown-linux-gnu
set -euo pipefail

MODE="${1:-portable}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' app/__init__.py)"
ARCH="${ARCH:-x86_64}"

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
fi

case "$MODE" in
  portable) NAME="docdiff-${VERSION}-linux-${ARCH}" ;;
  docker)   PLATFORM="${PLATFORM:-linux/amd64}"; NAME="docdiff-${VERSION}-docker-${PLATFORM#linux/}" ;;
  venv)     NAME="docdiff-${VERSION}-venv-py${PY_VERSION:-3.11}-${ARCH}" ;;
  *) echo "Использование: $0 portable|docker|venv" >&2; exit 1 ;;
esac
STAGE="dist/${NAME}/docdiff"

rm -rf "dist/${NAME}" "dist/${NAME}.tar.gz"
mkdir -p "$STAGE/deploy"
cp README.md .env.example "$STAGE/"
mkdir -p "$STAGE/docs" && cp -r docs/wiki "$STAGE/docs/"
cp scripts/install.sh "$STAGE/install.sh"
cp deploy/docdiff.service deploy/nginx.conf.example "$STAGE/deploy/"
chmod +x "$STAGE/install.sh"

copy_app() {
  cp -r app requirements.txt "$STAGE/"
  find "$STAGE/app" -name __pycache__ -prune -exec rm -rf {} +
}

case "$MODE" in
  portable)
    PBS_TAG="${PBS_TAG:-20260924}"
    PBS_PY="${PBS_PY:-3.11.16}"
    TRIPLE="${PORTABLE_TRIPLE:-${ARCH}-unknown-linux-gnu}"
    # manylinux2014 (glibc 2.17) — запустится даже на CentOS 7 / RHEL 7
    PIP_PLATFORMS="${PIP_PLATFORMS:-manylinux2014_${ARCH} manylinux_2_17_${ARCH}}"
    URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_PY}+${PBS_TAG}-${TRIPLE}-install_only_stripped.tar.gz"
    echo ">> Portable Python ${PBS_PY} (${TRIPLE})"
    curl -fsSL "$URL" | tar xz -C "$STAGE"          # → $STAGE/python
    plat_args=(); for p in $PIP_PLATFORMS; do plat_args+=(--platform "$p"); done
    echo ">> Установка зависимостей в lib/"
    "$PY" -m pip install -q --disable-pip-version-check --only-binary=:all: \
      --implementation cp --python-version "${PBS_PY%.*}" "${plat_args[@]}" \
      --target "$STAGE/lib" -r requirements.txt
    find "$STAGE/lib" -name __pycache__ -prune -exec rm -rf {} +
    copy_app
    cp scripts/start.sh scripts/docdiff-cli "$STAGE/"
    chmod +x "$STAGE/start.sh" "$STAGE/docdiff-cli"
    ;;
  docker)
    echo ">> Сборка образа docdiff:${VERSION} для ${PLATFORM} (LibreOffice: ${WITH_LIBREOFFICE:-0})"
    docker build --platform "$PLATFORM" \
      --build-arg WITH_LIBREOFFICE="${WITH_LIBREOFFICE:-0}" \
      -t "docdiff:${VERSION}" -t docdiff:latest .
    echo ">> Экспорт образа"
    docker save "docdiff:${VERSION}" docdiff:latest | gzip > "$STAGE/docdiff-image.tar.gz"
    cp docker-compose.yml "$STAGE/"
    ;;
  venv)
    PY_VERSION="${PY_VERSION:-3.11}"
    PIP_PLATFORMS="${PIP_PLATFORMS:-manylinux2014_${ARCH} manylinux_2_17_${ARCH} manylinux_2_28_${ARCH}}"
    plat_args=(); for p in $PIP_PLATFORMS; do plat_args+=(--platform "$p"); done
    echo ">> Скачивание колёс для Python ${PY_VERSION} / ${PIP_PLATFORMS}"
    "$PY" -m pip download -q --disable-pip-version-check --only-binary=:all: --implementation cp \
      --python-version "$PY_VERSION" "${plat_args[@]}" \
      -d "$STAGE/wheels" -r requirements.txt pip
    echo "$PY_VERSION" > "$STAGE/wheels/PYTHON_VERSION"
    copy_app
    ;;
esac

tar -C "dist/${NAME}" -czf "dist/${NAME}.tar.gz" docdiff
rm -rf "dist/${NAME}"
echo
echo "Готово: dist/${NAME}.tar.gz ($(du -h "dist/${NAME}.tar.gz" | cut -f1 | tr -d ' '))"
echo "На сервере:  tar xzf ${NAME}.tar.gz && cd docdiff && sudo ./install.sh"
