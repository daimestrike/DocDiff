# Обновление и релизы

## Обновить сервис на сервере

1. Скачайте новый архив из [Releases](https://github.com/daimestrike/DocDiff/releases/latest).
2. Распакуйте **в новую папку** и перенесите настройки:

```bash
cd /opt
tar xzf docdiff-1.1.0-linux-x86_64.tar.gz -C /tmp
mv docdiff docdiff-old
mv /tmp/docdiff docdiff
cp docdiff-old/.env docdiff/
cd docdiff && sudo ./install.sh
```

3. Проверьте `http://<сервер>:8080` — версия видна в правом верхнем углу.
4. Если всё хорошо — `rm -rf /opt/docdiff-old`.

**Откат:** верните старую папку на место и снова `sudo ./install.sh`.

**Docker:** то же самое — новый `install.sh` загрузит новый образ и пересоздаст контейнер.

## Выпустить новую версию (для разработчиков)

Архивы собирает GitHub Actions автоматически по тегу.

```bash
# 1. поднять версию
sed -i '' 's/__version__ = ".*"/__version__ = "1.1.0"/' app/__init__.py   # на Linux без ''

# 2. закоммитить и поставить тег
git commit -am "v1.1.0"
git tag v1.1.0
git push && git push --tags
```

Что происходит дальше ([release.yml](https://github.com/daimestrike/DocDiff/blob/main/.github/workflows/release.yml)):

1. **test** — тесты `pytest`.
2. **portable** (x86_64 и aarch64) — сборка архива со встроенным Python, затем проверка: распаковка, `install.sh`, запуск, запрос к API, CLI.
3. **docker** — сборка образа, запуск контейнера, проверка `/health`.
4. **release** — публикация трёх архивов и `SHA256SUMS.txt` в Releases.

Ход сборки — вкладка [Actions](https://github.com/daimestrike/DocDiff/actions). Обычно занимает 3–5 минут.

## Версии зависимостей

Все библиотеки зафиксированы в `requirements.txt`, Python для портативной сборки — в `scripts/build_bundle.sh` (`PBS_TAG`, `PBS_PY`). Чтобы обновить — поменяйте версии, прогоните `make test` и выпустите новый тег.

---

← [CLI и API](07-cli-and-api.md) · [Оглавление](README.md) · [Решение проблем](09-troubleshooting.md) →
