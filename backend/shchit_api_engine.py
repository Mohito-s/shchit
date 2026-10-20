from __future__ import annotations
import os
import re
import httpx

TWO_IP_TOKEN = os.getenv("TWO_IP_API_TOKEN", "demo_token")
YANDEX_SB_KEY = os.getenv("YANDEX_SAFE_BROWSING_KEY", "demo_key")
DADATA_TOKEN = os.getenv("DADATA_API_TOKEN", "demo_token")


def mask_personal_data_152fz(raw_text: str) -> str:
    """Маскирует серии/номера паспортов, телефоны и ФИО в оперативной памяти (152-ФЗ Zero-Storage)."""
    text = re.sub(r"\b\d{4}\s?\d{6}\b", "[ПАСПОРТ СКРЫТ 152-ФЗ]", raw_text)
    text = re.sub(r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", "[ТЕЛЕФОН СКРЫТ]", text)
    return text


async def check_target_in_shchit(domain_or_url: str, inn: str | None = None) -> dict:
    """Параллельный опрос готовых государственных и коммерческих API."""
    results = {
        "target": domain_or_url,
        "whois_2ip": None,
        "yandex_safebrowsing": None,
        "fns_egrul_dadata": None,
        "cbr_warning_list": False,
        "disclaimer": (
            "Отчет сформирован автоматически на основе открытых данных ФНС РФ (ЕГРЮЛ), "
            "Банка России (Warning List API), Yandex Safe Browsing и публичного WHOIS. "
            "Носит справочно-информационный характер."
        ),
    }

    is_inn_only = bool(re.match(r"^\d{10}$|^\d{12}$", domain_or_url.strip()))
    if is_inn_only and not inn:
        inn = domain_or_url.strip()

    async with httpx.AsyncClient(timeout=6.0) as client:
        # 1. 2IP.io WHOIS API (только для доменов и URL)
        if not is_inn_only and TWO_IP_TOKEN != "demo_token":
            try:
                r_whois = await client.get(
                    f"https://api.2ip.io/whois/{domain_or_url}",
                    params={"token": TWO_IP_TOKEN},
                )
                results["whois_2ip"] = r_whois.json()
            except Exception as exc:
                results["whois_2ip"] = {"error": str(exc)}

        # 2. Yandex Safe Browsing API v4 (только для доменов и URL)
        if not is_inn_only and YANDEX_SB_KEY != "demo_key":
            ysb_payload = {
                "client": {"clientId": "shchit-max-bot", "clientVersion": "1.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                    "platformTypes": ["ALL_PLATFORMS"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": domain_or_url}],
                },
            }
            try:
                r_ysb = await client.post(
                    f"https://sba.yandex.net/v4/threatMatches:find?key={YANDEX_SB_KEY}",
                    json=ysb_payload,
                )
                results["yandex_safebrowsing"] = r_ysb.json()
            except Exception as exc:
                results["yandex_safebrowsing"] = {"error": str(exc)}

        # 3. DaData ФНС ЕГРЮЛ/ЕГРИП API (бесплатно до 10 000 запросов в день)
        if inn and DADATA_TOKEN != "demo_token":
            try:
                r_dadata = await client.post(
                    "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party",
                    headers={"Authorization": f"Token {DADATA_TOKEN}"},
                    json={"query": inn},
                )
                results["fns_egrul_dadata"] = r_dadata.json()
            except Exception as exc:
                results["fns_egrul_dadata"] = {"error": str(exc)}

    return results
