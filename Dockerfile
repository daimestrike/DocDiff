FROM python:3.11-slim

# 1 — поставить LibreOffice для поддержки .doc/.rtf/.odt/.ppt (образ вырастет на ~600 МБ)
ARG WITH_LIBREOFFICE=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    PORT=8080

RUN if [ "$WITH_LIBREOFFICE" = "1" ]; then \
      apt-get update && \
      apt-get install -y --no-install-recommends libreoffice-writer libreoffice-calc libreoffice-impress && \
      rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN useradd --system --uid 10001 --no-create-home docdiff
USER docdiff

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/health', timeout=3)"

CMD ["python", "-m", "app"]
