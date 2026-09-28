PY ?= python3
VENV = .venv/bin

.PHONY: help install run test examples demo bundle-portable bundle-docker bundle-venv docker-build up down clean

help:            ## Список команд
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

install:         ## Создать .venv и поставить зависимости
	$(PY) -m venv .venv && $(VENV)/pip install -q -r requirements-dev.txt

run:             ## Запустить локально на http://localhost:8080
	./run.sh

test:            ## Прогнать тесты
	$(VENV)/python -m pytest -q

examples:        ## Сгенерировать демо-файлы в examples/
	$(VENV)/python scripts/make_examples.py

demo: examples   ## Сравнить демо-файлы в терминале
	-$(VENV)/python -m app.cli examples/contract_v1.docx examples/contract_v2.docx
	-$(VENV)/python -m app.cli examples/price_v1.xlsx examples/price_v2.xlsx --html examples/report.html

bundle-portable: ## Офлайн-пакет: Python + зависимости внутри → dist/ (ARCH=x86_64|aarch64)
	scripts/build_bundle.sh portable

bundle-docker:   ## Офлайн-пакет: Docker-образ + compose → dist/
	scripts/build_bundle.sh docker

bundle-venv:     ## Офлайн-пакет: колёса под системный Python сервера → dist/
	scripts/build_bundle.sh venv

docker-build:    ## Собрать образ локально
	docker build -t docdiff:latest .

up:              ## Поднять через docker compose
	docker compose up -d

down:            ## Остановить docker compose
	docker compose down

clean:           ## Удалить dist/ и кэши
	rm -rf dist .pytest_cache; find . -name __pycache__ -prune -exec rm -rf {} +
