"""HTTP API и отдача веб-интерфейса."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from . import __version__, config
from .differ import Options, compare_files
from .parsers import UnsupportedFormat, soffice_path, supported_extensions

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="DocDiff", version=__version__, docs_url="/api/docs", redoc_url=None)


def _read(f: UploadFile) -> bytes:
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    data = f.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"Файл «{f.filename}» больше {config.MAX_UPLOAD_MB} МБ")
    return data


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/api/info")
def info():
    return {"version": __version__, "extensions": supported_extensions(),
            "libreoffice": bool(soffice_path()), "max_upload_mb": config.MAX_UPLOAD_MB}


# Синхронный обработчик: FastAPI выполнит его в пуле потоков, не блокируя event loop
@app.post("/api/compare")
def compare(
    file_a: UploadFile = File(..., description="Исходный документ («было»)"),
    file_b: UploadFile = File(..., description="Новый документ («стало»)"),
    ignore_case: bool = Form(False),
    ignore_whitespace: bool = Form(False),
):
    opts = Options(ignore_case=ignore_case, ignore_whitespace=ignore_whitespace)
    try:
        return compare_files(_read(file_a), file_a.filename or "a",
                             _read(file_b), file_b.filename or "b", opts)
    except UnsupportedFormat as e:
        raise HTTPException(415, str(e)) from e
