"""
backend/telegram_bot.py
Легковесный и автономный модуль Telegram-бота @Anti_scamX_bot.
- Поддерживает команды /start (с deep-linking и UTM-метками), /help, /admin (для Романа).
- Проверяет ИНН организаций и ИП через DaData ФНС и реестр пирамид ЦБ РФ.
- Проверяет ссылки и домены на фишинг через 2IP WHOIS и черные списки.
- Читает PDF-документы прямо в чате строго в оперативной памяти (152-ФЗ Zero-Storage) и находит скрытые навязанные услуги автосалонов/банков.
- Поддерживает опциональный TELEGRAM_PROXY_URL при запуске в РФ.
"""
import os
import io
import re
import asyncio
import logging
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader

load_dotenv()

from .shchit_api_engine import check_target_in_shchit, mask_personal_data_152fz

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "roman_shchit_secret_2026")
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL") or None
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://shchit-audit.ru")
CHANNEL_USERNAME = os.getenv("TELEGRAM_CHANNEL_USERNAME", "antiscam_domens")
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "Anti_scamX_bot")

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


async def send_welcome(client: httpx.AsyncClient, chat_id: int, utm_source: str | None = None):
    # Логирование источника без сбора персональных данных (152-ФЗ Zero-Storage)
    if utm_source:
        logger.info(f"[ANON_METRICS_152FZ] New user lead: source={utm_source}, chat_id={chat_id}")

    if utm_source and "pikabu" in utm_source.lower():
        text = (
            "🛡️ **Привет с Пикабу!**\n\n"
            "Вы перешли из нашего разбора схем мошенников. Бот «ЩИТ» помогает не потерять деньги "
            "и аккаунты перед оплатой или переходом.\n\n"
            "🔍 **Что можно проверить прямо сейчас:**\n"
            "1. **Ссылку или сайт** — на фишинг, поддельные опросы и дату создания\n"
            "2. **ИНН компании** (10-12 цифр) — легальность в ФНС, однодневка ли это, черный список ЦБ РФ\n"
            "3. **Договор (PDF)** — прикрепите файл, и я найду навязанные допуслуги автосалонов/банков\n\n"
            "Просто отправьте ссылку, ИНН или файл в этот чат!"
        )
    else:
        text = (
            "🛡️ **Добро пожаловать в сервис «ЩИТ»!**\n\n"
            "Я помогаю за 3–5 секунд проверить подозрительную ссылку, ИНН организации или договор "
            "перед оплатой, защищая от фишинга, угона аккаунтов и навязанных услуг.\n\n"
            "🔍 **Что мне можно отправить прямо в чат:**\n"
            "• 🔗 **Ссылку** (например, с голосованием или выплатой СБП)\n"
            "• 🏢 **ИНН компании** (10 или 12 цифр)\n"
            "• 📄 **PDF-документ** (кредитный договор или сертификат автосалона)\n\n"
            "Либо нажмите кнопку ниже для запуска полноэкранного сканера."
        )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🛡️ Открыть веб-сканер «ЩИТ»",
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
                        "switch_inline_query": f"Внимание! Проверяйте ссылки и ИНН перед оплатой через @{BOT_USERNAME}"
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


async def analyze_and_reply_inn(client: httpx.AsyncClient, chat_id: int, inn: str):
    await tg_request(client, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
    result = await check_target_in_shchit(domain_or_url=inn, inn=inn)

    dadata = result.get("fns_egrul_dadata") or {}
    suggestions = dadata.get("suggestions") or []
    cbr_warning = result.get("cbr_warning_list", False)

    if not suggestions:
        text = (
            f"⚠️ **ИНН `{inn}` не найден в базах ФНС (ЕГРЮЛ / ЕГРИП)**\n\n"
            f"Организация или ИП с таким номером в официальном реестре не числится.\n\n"
            f"**Возможные причины:**\n"
            f"• Опечатка в номере реквизитов\n"
            f"• Фиктивная компания / мошенники назвали чужой или случайный номер\n\n"
            f"• Реестр ЦБ РФ: {'🚨 НАЙДЕН В СПИСКЕ ПИРАМИД!' if cbr_warning else 'В черном списке не значится'}\n\n"
            f"💡 **Рекомендация:** Не переводите средства и не подписывайте документы с этим ИНН до проверки на egrul.nalog.ru."
        )
    else:
        company = suggestions[0].get("data") or {}
        name = suggestions[0].get("value") or inn
        status = company.get("state", {}).get("status", "UNKNOWN")
        is_active = status == "ACTIVE"
        is_liquidated = status == "LIQUIDATED"
        ogrn = company.get("ogrn") or "—"
        address = company.get("address", {}).get("value") or "—"
        okved = company.get("okved") or "—"
        company_type = "ООО / АО (Юрлицо)" if company.get("type") == "LEGAL" else "Индивидуальный предприниматель (ИП)"

        if is_active:
            status_text = "✅ **Действующая организация**"
        elif is_liquidated:
            status_text = "❌ **ОРГАНИЗАЦИЯ ЛИКВИДИРОВАНА**"
        else:
            status_text = f"⚠️ Статус: `{status}`"

        cbr_text = "🚨 **ВНИМАНИЕ: Числится в черном списке пирамид Банка России!**" if cbr_warning else "✅ Реестр ЦБ РФ: в черном списке пирамид не найден"

        text = (
            f"🏢 **Результат проверки по ЕГРЮЛ ФНС:**\n\n"
            f"**Название:** `{name}`\n"
            f"**Статус:** {status_text}\n"
            f"**Тип:** {company_type}\n"
            f"**ИНН:** `{inn}` • **ОГРН:** `{ogrn}`\n"
            f"**Адрес:** {address}\n"
            f"**ОКВЭД:** `{okved}`\n\n"
            f"{cbr_text}\n\n"
            f"💡 **Рекомендация:** "
            f"{'Компания действует. Дополнительно сверьте реквизиты в счёте.' if is_active and not cbr_warning else 'ОПАСНО: Не переводите деньги! Организация либо закрыта, либо находится под санкцией регулятора.'}"
        )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🛡️ Проверить в полном веб-сканере",
                        "web_app": {"url": WEBAPP_URL}
                    }
                ]
            ]
        }
    }
    await tg_request(client, "sendMessage", payload)


async def analyze_and_reply_url(client: httpx.AsyncClient, chat_id: int, user_input: str):
    await tg_request(client, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
    result = await check_target_in_shchit(user_input.strip())
    
    is_cbr = bool(result.get("cbr_warning_list"))
    has_threat = bool(result.get("yandex_safebrowsing", {}).get("threatMatches"))
    is_suspect = is_cbr or has_threat
    icon = "🚨 ОПАСНОСТЬ" if is_suspect else "✅ БЕЗОПАСНО"
    
    report = (
        f"{icon}\n"
        f"**Объект проверки:** `{user_input}`\n\n"
        f"**Сводка экспресс-анализа:**\n"
        f"• Реестр ЦБ РФ: {'🚨 НАЙДЕН в черном списке финансовых пирамид!' if is_cbr else 'Легальный статус / нет в реестре пирамид'}\n"
        f"• Угрозы фишинга: {'🚨 Обнаружены признаки опасного сайта!' if has_threat else 'Явных вредоносных маркеров не найдено'}\n"
        f"• Проверка выполнена в оперативной памяти (152-ФЗ Zero-Storage)\n\n"
        f"💡 **Рекомендация:** "
        f"{'Не переходите по ссылке и не вводите личные данные или СМС-коды!' if is_suspect else 'Явных признаков фишинга не найдено, соблюдайте базовую бдительность.'}"
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


async def analyze_and_reply_pdf(client: httpx.AsyncClient, chat_id: int, doc_info: dict):
    file_id = doc_info.get("file_id")
    file_name = doc_info.get("file_name", "договор.pdf")

    await tg_request(client, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
    await tg_request(client, "sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ Загружаю и сканирую «{file_name}» в оперативной памяти (Zero-Storage 152-ФЗ)..."
    })

    file_meta = await tg_request(client, "getFile", {"file_id": file_id})
    if not file_meta or not file_meta.get("file_path"):
        await tg_request(client, "sendMessage", {
            "chat_id": chat_id,
            "text": "❌ Не удалось прочитать файл. Пожалуйста, отправьте его повторно."
        })
        return

    file_path = file_meta["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    try:
        res = await client.get(download_url, timeout=30.0)
        raw_bytes = res.content
        ram_buffer = io.BytesIO(raw_bytes)
        reader = PdfReader(ram_buffer)
        
        extracted_pages = [page.extract_text() or "" for page in reader.pages[:10]]
        full_text = "\n".join(extracted_pages)
        clean_text = mask_personal_data_152fz(full_text)
        ram_buffer.close()

        # Поиск навязанных услуг и кабальных пунктов
        predatory_markers = []
        lower_text = clean_text.lower()
        if "помощь на дорог" in lower_text or "ассистанс" in lower_text:
            predatory_markers.append("Сертификат помощи на дорогах (авто-ассистанс)")
        if "опцион" in lower_text:
            predatory_markers.append("Опционный договор / сертификат")
        if "абонентск" in lower_text:
            predatory_markers.append("Абонентский договор с фиксированной оплатой")
        if "телемедицин" in lower_text or "консультационн" in lower_text:
            predatory_markers.append("Пакет телемедицины / юридических консультаций")
        if "возврату не подлежит" in lower_text or "считаются оказанными" in lower_text:
            predatory_markers.append("Пункт о «невозвратности» средств (противоречит ЗоЗПП)")

        # Поиск ИНН компаний в документе
        inns = list(set(re.findall(r"\b\d{10}\b", clean_text)))

        if predatory_markers:
            markers_list = "\n".join([f"• ⚠️ {m}" for m in predatory_markers])
            inn_info = f"\n**Найденные ИНН в документе:** `{', '.join(inns[:3])}`" if inns else ""

            text = (
                f"📄 **Экспертиза документа «{file_name}»:**\n\n"
                f"🚨 **Обнаружены признаки навязанных услуг:**\n"
                f"{markers_list}{inn_info}\n\n"
                f"⚖️ **Правовой анализ (ст. 16 и 32 ЗоЗПП, ст. 782 ГК РФ):**\n"
                f"Условия о «невозвратности» денег по закону РФ являются **ничтожными**. "
                f"Вы имеете полное право отказаться от навязанной услуги в течение «периода охлаждения» (30 дней) "
                f"и потребовать возврат 100% уплаченных средств.\n\n"
                f"💼 Хотите сформировать официальную досудебную претензию с реквизитами исполнителя за **190 ₽**?"
            )
            buttons = [
                [
                    {
                        "text": "📄 Сформировать досудебную претензию (190 ₽)",
                        "web_app": {"url": f"{WEBAPP_URL}?action=claim"}
                    }
                ]
            ]
        else:
            text = (
                f"📄 **Экспертиза документа «{file_name}»:**\n\n"
                f"✅ Явных кабальных пунктов об отказе в возврате или навязанных сертификатов помощи на дорогах в первых 10 страницах не обнаружено.\n\n"
                f"Обработка выполнена строго в оперативной памяти (Zero-Storage 152-ФЗ, файл не сохранён на диск)."
            )
            buttons = [
                [
                    {
                        "text": "🛡️ Открыть сканер «ЩИТ»",
                        "web_app": {"url": WEBAPP_URL}
                    }
                ]
            ]

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": buttons}
        }
        await tg_request(client, "sendMessage", payload)

    except Exception as e:
        logger.error(f"Error parsing PDF in bot: {e}")
        await tg_request(client, "sendMessage", {
            "chat_id": chat_id,
            "text": "⚠️ Не удалось распознать текст PDF (возможно, документ содержит только отсканированные изображения без текстового слоя)."
        })


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
                        if not msg:
                            continue
                        
                        chat_id = msg["chat"]["id"]

                        # 1. Проверка документов (PDF)
                        doc = msg.get("document")
                        if doc and (doc.get("mime_type") == "application/pdf" or str(doc.get("file_name", "")).endswith(".pdf")):
                            await analyze_and_reply_pdf(client, chat_id, doc)
                            continue

                        # 2. Текстовые сообщения
                        text = msg.get("text", "").strip()
                        if not text:
                            continue

                        if text.startswith("/start"):
                            parts = text.split(maxsplit=1)
                            utm_source = parts[1] if len(parts) > 1 else None
                            await send_welcome(client, chat_id, utm_source)
                        elif text in ("/admin", "/crm"):
                            await send_admin_panel(client, chat_id)
                        elif re.match(r"^\d{10}$|^\d{12}$", text):
                            await analyze_and_reply_inn(client, chat_id, text)
                        else:
                            await analyze_and_reply_url(client, chat_id, text)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле polling бота: {e}")
                await asyncio.sleep(4)


if __name__ == "__main__":
    asyncio.run(run_bot_polling())
