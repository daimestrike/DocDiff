# Разработка

## Локальный запуск

Нужен Python 3.9+.

```bash
git clone https://github.com/daimestrike/DocDiff.git && cd DocDiff
./run.sh                # создаст .venv, поставит зависимости → http://localhost:8080
```

## Команды

```bash
make help        # список команд
make install     # .venv + зависимости
make run         # запуск
make test        # тесты
make examples    # демо-файлы в examples/
make demo        # сравнить демо-файлы в терминале + examples/report.html
make bundle-portable | bundle-docker | bundle-venv   # офлайн-архивы в dist/
make clean
```

## Структура репозитория

```
app/                  приложение (см. Архитектура)
tests/test_diff.py    тесты
examples/             демо-файлы: договор (Word) и прайс (Excel), по две версии
scripts/
  build_bundle.sh     сборка офлайн-архивов
  install.sh          установка на сервере (кладётся в архив)
  start.sh, docdiff-cli  запуск портативной версии (кладутся в архив)
  make_examples.py    генерация демо-файлов
deploy/               шаблоны systemd и nginx
wiki/                 документация проекта (эти страницы)
.github/workflows/    CI и сборка релизов
Dockerfile, docker-compose.yml
```

## Тесты

```bash
make test
```

Тесты генерируют Word/Excel-файлы на лету и проверяют: текстовое сравнение, опции нормализации, вставку строк и изменение ячеек в Excel, добавление/удаление листов, CSV в Windows-1251, смешанные форматы, HTTP API.

CI ([ci.yml](https://github.com/daimestrike/DocDiff/blob/main/.github/workflows/ci.yml)) прогоняет их на каждый push в `main` и в pull request.

## Документация

Документация — папка `wiki/` в корне репозитория, обычные markdown-файлы:

- номер в имени файла задаёт порядок чтения, [README.md](README.md) — оглавление;
- ссылки между документами относительные (`[Установка](03-installation.md)`), поэтому работают и на GitHub, и в распакованном архиве;
- внизу каждого документа — навигация «назад / оглавление / далее»; добавляя новый документ, обновите её у соседей и в оглавлении;
- `scripts/build_bundle.sh` кладёт папку `wiki/` в каждый офлайн-архив.

---

← [Архитектура](10-architecture.md) · [Оглавление](README.md)
