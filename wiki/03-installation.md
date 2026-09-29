# Установка

Все варианты рассчитаны на сервер **без интернета**: архив собирается заранее и содержит всё нужное. `install.sh` сам определяет тип архива.

| Вариант | Что нужно на сервере | Размер | Когда выбирать |
|---|---|---|---|
| **A. Портативный** | Linux x86_64/aarch64, glibc ≥ 2.17 | ~48 МБ | По умолчанию |
| **B. Docker** | Docker + compose | ~67 МБ | Если сервисы в контуре живут в Docker |
| **C. Системный Python** | Python 3.9+ | ~18 МБ | Если политика запрещает приносить свой интерпретатор |

Архивы A и B — готовые в [Releases](https://github.com/daimestrike/DocDiff/releases/latest). C собирается самостоятельно.

---

## A. Портативный (рекомендуется)

Внутри архива: Python 3.11 ([python-build-standalone](https://github.com/astral-sh/python-build-standalone)), все библиотеки и приложение. Ничего не устанавливается в систему — всё лежит в одной папке.

Подходит для: CentOS 7+, RHEL 7+, Astra Linux, РЕД ОС, ALT, Debian, Ubuntu и других Linux с glibc 2.17+.

```bash
tar xzf docdiff-1.0.0-linux-x86_64.tar.gz && cd docdiff
sudo ./install.sh
```

Состав архива:

```
docdiff/
├── install.sh       установка systemd-сервиса
├── start.sh         запуск вручную
├── docdiff-cli      сравнение из командной строки
├── .env.example     настройки (копируется в .env)
├── python/          встроенный Python
├── lib/             библиотеки
├── app/             приложение
├── deploy/          шаблоны systemd и nginx
├── wiki/            эта документация
└── README.md
```

## B. Docker

```bash
tar xzf docdiff-1.0.0-docker-amd64.tar.gz && cd docdiff
sudo ./install.sh
```

Скрипт выполнит `docker load`, создаст `.env` и запустит `docker compose up -d`. Контейнер:
- перезапускается автоматически (`restart: unless-stopped`);
- работает с read-only файловой системой, временные файлы — в tmpfs;
- ограничивает логи (3 файла по 10 МБ).

Работает и с `docker compose` (v2), и со старым `docker-compose`.

## C. Под системный Python сервера

Собирается на машине с интернетом из исходников под **ту же минорную версию** Python, что на сервере.

```bash
# на сервере
python3 --version          # например, Python 3.11.2

# на машине с интернетом, в клоне репозитория
PY_VERSION=3.11 make bundle-venv
# → dist/docdiff-1.0.0-venv-py3.11-x86_64.tar.gz

# на сервере
tar xzf docdiff-1.0.0-venv-py3.11-x86_64.tar.gz && cd docdiff
sudo ./install.sh
```

- Если в системе нет пакета `python3-venv`, скрипт поставит pip из колеса в архиве.
- Другой интерпретатор: `sudo PYTHON=/usr/bin/python3.12 ./install.sh`.
- Сервер с glibc < 2.28: `PIP_PLATFORMS="manylinux2014_x86_64" PY_VERSION=3.9 make bundle-venv`.

---

## Параметры install.sh

| Переменная | Действие |
|---|---|
| `NO_SYSTEMD=1` | Не ставить systemd-сервис, только подготовить и показать команду запуска |
| `PYTHON=/path/python3` | Интерпретатор для варианта C |

## Что делает install.sh с systemd

- создаёт пользователя `docdiff` (без shell и домашней папки);
- ставит `/etc/systemd/system/docdiff.service` с защитой (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=full`);
- включает автозапуск и ждёт ответа `/health`.

Управление:

```bash
systemctl status docdiff
systemctl restart docdiff
journalctl -u docdiff -f
```

## Удаление

```bash
sudo systemctl disable --now docdiff
sudo rm /etc/systemd/system/docdiff.service
sudo rm -rf /opt/docdiff
sudo userdel docdiff
```

Docker: `cd /opt/docdiff && docker compose down && docker rmi docdiff:latest docdiff:1.0.0`.

## Собрать архив самому

Нужна машина с интернетом (подойдёт Mac, в том числе на Apple Silicon):

```bash
git clone https://github.com/daimestrike/DocDiff.git && cd DocDiff
make bundle-portable                    # портативный x86_64
ARCH=aarch64 make bundle-portable       # портативный ARM
make bundle-docker                      # Docker (нужен docker)
PLATFORM=linux/arm64 make bundle-docker # Docker для ARM
```

Результат — в `dist/`.

---

← [Быстрый старт](02-quick-start.md) · [Оглавление](README.md) · [Руководство пользователя](04-user-guide.md) →
