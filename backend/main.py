import io
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

from .shchit_api_engine import check_target_in_shchit, mask_personal_data_152fz
from .comment_hub import notify_roman_in_max, send_reply_to_platform

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "roman_shchit_secret_2026")

app = FastAPI(title="ЩИТ • Анти-скам & Проверка документов в MAX")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_PATH = BASE_DIR / "frontend" / "index.html"
ADMIN_FRONTEND_PATH = BASE_DIR / "frontend" / "admin.html"
PUBLIC_PATH = BASE_DIR / "public"


class ScanUrlRequest(BaseModel):
    url_or_domain: str
    inn: str | None = None


class CommentReplyRequest(BaseModel):
    platform: str
    ext_id: str
    reply_text: str


@app.get("/", response_class=HTMLResponse)
async def serve_mini_app():
    """Контур 1: Публичный Клиентский сканер (Zero-Trust, 0% кода админки)."""
    if FRONTEND_PATH.exists():
        return FRONTEND_PATH.read_text(encoding="utf-8")
    return "<h1>Щит работает</h1>"


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_app(
    key: str | None = Query(None),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key")
):
    """
    Контур 2: Изолированная личная CRM Романа (Zero-Trust).
    Доступ только по секретному ключу из .env или проверенному токену админа в MAX/TG.
    """
    provided_key = key or x_admin_key
    if not provided_key or provided_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: контур личной CRM Романа защищен Zero-Trust ключом."
        )
    if ADMIN_FRONTEND_PATH.exists():
        return ADMIN_FRONTEND_PATH.read_text(encoding="utf-8")
    return "<h1>Админка не найдена</h1>"


@app.get("/robots.txt", response_class=PlainTextResponse)
async def serve_robots():
    f = PUBLIC_PATH / "robots.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


@app.get("/llms.txt", response_class=PlainTextResponse)
async def serve_llms():
    f = PUBLIC_PATH / "llms.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


@app.post("/api/scan/url")
async def api_scan_url(req: ScanUrlRequest):
    return await check_target_in_shchit(req.url_or_domain, req.inn)


@app.post("/api/scan/pdf-zero-storage")
async def api_scan_pdf_in_ram(file: UploadFile = File(...)):
    """Читает PDF строго в оперативной памяти (io.BytesIO) и удаляет без записи на диск (152-ФЗ)."""
    raw_bytes = await file.read()
    ram_buffer = io.BytesIO(raw_bytes)
    reader = PdfReader(ram_buffer)
    metadata = dict(reader.metadata or {})
    extracted_pages = [page.extract_text() or "" for page in reader.pages[:5]]
    clean_text = mask_personal_data_152fz("\n".join(extracted_pages))
    ram_buffer.close()
    return {
        "filename": file.filename,
        "storage_mode": "RAM_ZERO_STORAGE_152FZ",
        "pdf_metadata": metadata,
        "masked_preview": clean_text[:600],
    }


@app.post("/api/admin/comments/reply")
async def api_reply_to_comment(
    req: CommentReplyRequest,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    key: str | None = Query(None)
):
    provided_key = x_admin_key or key
    if not provided_key or provided_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Доступ к отправке комментариев закрыт: неверный ключ авторизации."
        )
    return await send_reply_to_platform(req.platform, req.ext_id, req.reply_text)
