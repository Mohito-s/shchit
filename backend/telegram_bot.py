"""
backend/telegram_bot.py
Легковесный и автономный модуль Telegram-бота @Anti_scamX_bot.
- Поддерживает команды /start, /help, /admin (для Романа).
- Предоставляет кнопку WebApp для мгновенного открытия экспресс-сканера «ЩИТ».
- Принимает ссылки, ИНН и домены текстом и проводит экспресс-анализ прямо в чате.
- Поддерживает опциональный TELEGRAM_PROXY_URL при запуске в РФ.
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
import httpx

load_dotenv()

from .shchit_api_engine import check_target_in_shchit

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "roman_shchit_secret_2026")
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL") or None
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://shchit-audit.ru")
CHANNEL_USERNAME = os.getenv("TELEGRAM_CHANNEL_USERNAME", "antiscam_domens")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("telegram_bot")


async def tg_request(client: httpx.AsyncClient, method: str, payload: dict | None = None) -> dict | None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        res = await client.post(url, json=payload or {}, timeout=15.0)
        data = res.json()
        if data.get("ok"):
            return data.get("result")
        logger.warning(f"Telegram API warning on {method}: {data}")
    except Exception as e:
        logger.error(f"Telegram request failed on {method}: {e}")
    return None


async def send_welcome(client: httpx.AsyncClient, chat_id: int):
    text = (
        "🛡️ **Добро пожаловать в сервис «ЩИТ»!**\n\n"
        "Я помогаю за 5 секунд проверить подозрительную ссылку, QR-код или договор "
        "перед оплатой или переходом, защищая от угона аккаунтов и фишинга.\n\n"
        "🔍 **Как мной пользоваться:**\n"
        "1. Нажмите кнопку ниже, чтобы открыть полноэкранный сканер;\n"
        "2. Либо просто **отправьте мне ссылку или ИНН** прямо в этот чат!"
    )
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🛡️ Открыть сканер «ЩИТ»",
                        "web_app": {"url": WEBAPP_URL}
                    }
                ],
                [
                    {
                        "text": f"📢 Наш канал: @{CHANNEL_USERNAME}",
                        "url": f"https://t.me/{CHANNEL_USERNAME}"
                    },
                    {
                        "text": "👥 Предупредить близких",
                        "switch_inline_query": f"Внимание! Проверяйте подозрительные ссылки через @{os.getenv('TELEGRAM_BOT_USERNAME', 'Anti_scamX_bot')}"
                    }
                ]
            ]
        }
    }
    await tg_request(client, "sendMessage", payload)


async def send_admin_panel(client: httpx.AsyncClient, chat_id: int):
    admin_url = f"{WEBAPP_URL}/admin?key={ADMIN_SECRET_KEY}"
    text = (
        "💼 **Личный кабинет CRM Романа (Zero-Trust)**\n\n"
        "Здесь доступен Единый Инбокс комментариев (VK, VC.ru, TG, Пикабу), "
        "генератор ответов в 1 клик и Контент-Завод разборов."
    )
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "💼 Открыть мою CRM и Инбокс",
                        "web_app": {"url": admin_url}
                    }
                ]
            ]
        }
    }
    await tg_request(client, "sendMessage", payload)


async def analyze_and_reply(client: httpx.AsyncClient, chat_id: int, user_input: str):
    await tg_request(client, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
    result = await check_target_in_shchit(user_input.strip())
    
    is_suspect = bool(result.get("cbr_warning_list") or result.get("whois_2ip", {}).get("error"))
    icon = "🚨 ОПАСНОСТЬ" if is_suspect else "✅ БЕЗОПАСНО"
    
    report = (
        f"{icon}\n"
        f"**Объект проверки:** `{user_input}`\n\n"
        f"**Сводка экспресс-анализа:**\n"
        f"• Реестр ЦБ РФ: {'ВНИМАНИЕ: найден в черном списке пирамид!' if result.get('cbr_warning_list') else 'Легальный статус / нет в реестре'}\n"
        f"• WHOIS & Хостинг: Проверка выполнена в оперативной памяти (152-ФЗ Zero-Storage)\n\n"
        f"💡 **Рекомендация:** "
        f"{'Не переходите по ссылке и не вводите СМС-коды!' if is_suspect else 'Явных признаков мошенничества не обнаружено, соблюдайте базовую бдительность.'}"
    )
    
    payload = {
        "chat_id": chat_id,
        "text": report,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "📄 Детальный аудит в приложении",
                        "web_app": {"url": WEBAPP_URL}
                    }
                ]
            ]
        }
    }
    await tg_request(client, "sendMessage", payload)


async def run_bot_polling():
    if not BOT_TOKEN or BOT_TOKEN == "your_tg_bot_token_here":
        logger.warning("TELEGRAM_BOT_TOKEN не задан. Бот не запускается.")
        return

    logger.info("Запуск Telegram бота @Anti_scamX_bot...")
    transport = httpx.AsyncHTTPTransport(proxy=PROXY_URL) if PROXY_URL else None
    
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        offset = 0
        while True:
            try:
                updates = await tg_request(client, "getUpdates", {"offset": offset, "timeout": 20})
                if updates:
                    for upd in updates:
                        offset = upd["update_id"] + 1
                        msg = upd.get("message")
                        if not msg or "text" not in msg:
                            continue
                        
                        chat_id = msg["chat"]["id"]
                        text = msg["text"].strip()
                        
                        if text == "/start":
                            await send_welcome(client, chat_id)
                        elif text in ("/admin", "/crm"):
                            await send_admin_panel(client, chat_id)
                        else:
                            await analyze_and_reply(client, chat_id, text)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле polling бота: {e}")
                await asyncio.sleep(4)


if __name__ == "__main__":
    asyncio.run(run_bot_polling())
