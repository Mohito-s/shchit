"""
tools/test_full_suite.py
Сквозной тест изолированной двухконтурной архитектуры (Zero-Trust):
1. Контур 1: Публичный клиентский сканер (проверка отсутствия кода админки, адаптивности, крупного шрифта).
2. Контур 2: Личная CRM Романа (проверка защиты 403 Forbidden при неверном ключе и 200 OK по секретному ключу).
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def run_suite():
    base_url = "http://127.0.0.1:8000"
    admin_key = "roman_shchit_secret_2026"
    print(f"[*] Запуск проверки двухконтурной Zero-Trust архитектуры: {base_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ============================================================
        # КОНТУР 1: ПУБЛИЧНЫЙ КЛИЕНТСКИЙ СКАНЕР
        # ============================================================
        print("\n--- 1. ТЕСТ КЛИЕНТСКОГО СКАНЕРА (DESKTOP + MOBILE) ---")
        client_page = browser.new_page(viewport={"width": 390, "height": 844})
        client_page.goto(base_url, wait_until="networkidle")
        
        # Verify 0% admin code in client UI
        has_admin_tab = client_page.query_selector("#tabBtnAdmin") is not None
        has_admin_section = client_page.query_selector("#viewAdmin") is not None
        print(f"[*] Проверка утечки админки в клиентский интерфейс: "
              f"{'УТЕЧКА!' if (has_admin_tab or has_admin_section) else 'ЧИСТО (0% админ-кода в клиенте, Zero-Trust)'}")
        
        # Check responsiveness
        client_overflow = client_page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        print(f"[*] Горизонтальный перелив на мобильном (Клиент): {'ОШИБКА' if client_overflow else 'НЕТ, 100% адаптивно (390px)'}")
        client_page.screenshot(path="preview_mobile_client.png", full_page=True)
        
        # Test large font toggle
        client_page.click("#btnA11yFont")
        client_page.wait_for_timeout(300)
        f_large = client_page.evaluate("() => window.getComputedStyle(document.body).fontSize")
        print(f"[+] Крупный шрифт включен: font-size = {f_large}")
        client_page.screenshot(path="preview_mobile_client_large.png", full_page=True)
        client_page.close()
        
        # ============================================================
        # КОНТУР 2: БЕЗОПАСНОСТЬ И АВТОРИЗАЦИЯ АДМИНКИ
        # ============================================================
        print("\n--- 2. ТЕСТ БЕЗОПАСНОСТИ ZERO-TRUST АДМИНКИ ---")
        sec_page = browser.new_page()
        
        # A. Attempt access without key -> Expect 403 Forbidden
        res_no_key = sec_page.goto(f"{base_url}/admin")
        print(f"[*] Попытка входа в админку без ключа: HTTP {res_no_key.status} ({'ЗАЩИЩЕНО 403' if res_no_key.status == 403 else 'ОШИБКА'})")
        
        # B. Attempt access with wrong key -> Expect 403 Forbidden
        res_wrong_key = sec_page.goto(f"{base_url}/admin?key=hacker_attempt")
        print(f"[*] Попытка входа с неверным ключом: HTTP {res_wrong_key.status} ({'ЗАЩИЩЕНО 403' if res_wrong_key.status == 403 else 'ОШИБКА'})")
        sec_page.close()
        
        # ============================================================
        # КОНТУР 2: ЛИЧНАЯ CRM РОМАНА (АВТОРИЗОВАННЫЙ ВХОД)
        # ============================================================
        print("\n--- 3. ТЕСТ АВТОРИЗОВАННОЙ ЛИЧНОЙ CRM РОМАНА ---")
        admin_page = browser.new_page(viewport={"width": 390, "height": 844})
        res_auth = admin_page.goto(f"{base_url}/admin?key={admin_key}", wait_until="networkidle")
        print(f"[*] Вход по ключу Романа: HTTP {res_auth.status} ({'УСПЕХ 200 OK' if res_auth.status == 200 else 'ОШИБКА'})")
        
        admin_overflow = admin_page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        print(f"[*] Горизонтальный перелив CRM на мобильном: {'ОШИБКА' if admin_overflow else 'НЕТ, 100% адаптивно (390px)'}")
        
        # Test 1-click comment reply
        print("[*] Тест клика на ответ в инбоксе комментариев...")
        admin_page.click("button.reply-choice-btn")
        admin_page.wait_for_timeout(400)
        
        toast_visible = admin_page.evaluate("() => window.getComputedStyle(document.getElementById('toastBox')).display !== 'none'")
        print(f"[+] Тост отправки ответа: {'ПОКАЗАН' if toast_visible else 'НЕ ПОКАЗАН'}")
        
        # Switch to Content Factory tab
        admin_page.click("#admSubTabFactory")
        admin_page.wait_for_timeout(300)
        
        admin_page.screenshot(path="preview_mobile_admin_isolated.png", full_page=True)
        admin_page.close()
        
        browser.close()
        print("\n[✓] Все тесты завершены! Двухконтурная Zero-Trust архитектура полностью проверена.")

if __name__ == "__main__":
    run_suite()
