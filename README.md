# ЩИТ (shchit-audit.ru / @shchit_check_bot) — Стартовый пакет для Google Antigravity

Единый анти-скам продукт (Мини-апп в MAX + Веб-сайт + Скрытая Админка с Единым Инбоксом Комментариев).

## Что внутри архива
1. `PROJECT_STATE.md` — главный контекстный файл для ИИ-агента в Google Antigravity.
2. `backend/main.py` — FastAPI сервер (Zero-Storage обработка PDF/QR в оперативной памяти по 152-ФЗ, вебхук для бота MAX и Скрытой Админки).
3. `backend/shchit_api_engine.py` — модуль интеграции 4 готовых внешних API (`2IP.io WHOIS`, `Yandex Safe Browsing v4`, `DaData ФНС ЕГРЮЛ`, `Warning List API ЦБ РФ`).
4. `backend/comment_hub.py` — **Единый Инбокс Комментариев для семьянина**: перехватывает комментарии под твоими статьями (ВК, VC.ru, Telegram, MAX, Пикабу, Хабр, Дзен), присылает тебе прямо в личку бота MAX уведомление и 3 готовых живых варианта ответа (через `anti-ai-humanizer`). Нажимаешь одну кнопку на телефоне — ответ улетает сам!
5. `frontend/index.html` — готовый фронтенд (Сканер клиента + Open Graph мета-теги + Скрытая Админка с Инбоксом комментариев).
6. `LEGAL_OFERTA_152FZ.md` — готовое Пользовательское соглашение и правовой дисклеймер для самозанятого (НПД).
7. `public/llms.txt` и `public/robots.txt` — GEO-конфиги для ИИ-поисковиков (ChatGPT, Perplexity, Алиса, Gemini).

## Быстрый старт вечером после работы (Ubuntu 24.04 / Локально в Antigravity)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```
Открой `http://localhost:8000` в браузере или в превью Google Antigravity.
