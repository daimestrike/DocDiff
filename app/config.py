"""Настройки приложения из переменных окружения."""
from __future__ import annotations

import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
WORKERS = int(os.getenv("WORKERS", "2"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
SOFFICE_TIMEOUT = int(os.getenv("SOFFICE_TIMEOUT", "60"))
