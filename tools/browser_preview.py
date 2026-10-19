"""
tools/browser_preview.py
Автоматизированный инструмент на Playwright для проверки интерфейса,
создания скриншотов (desktop/mobile) и валидации верстки проекта «ЩИТ».
"""
import sys
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def inspect_page(url: str, output_path: str = "screenshot.png", mobile: bool = False, toggle_large: bool = False):
    print(f"[*] Открываю {url} через Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        if mobile:
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            )
        else:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            
        page = context.new_page()
        
        console_messages = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        
        response = page.goto(url, wait_until="networkidle", timeout=15000)
        status = response.status if response else "Unknown"
        print(f"[+] HTTP Статус: {status}")

        initial_font_size = page.evaluate("() => window.getComputedStyle(document.body).fontSize")
        print(f"[*] Базовый размер шрифта: {initial_font_size}")

        if toggle_large:
            print("[*] Переключаю на 'Крупный шрифт'...")
            page.click("#btnA11yFont")
            page.wait_for_timeout(300)
            large_font_size = page.evaluate("() => window.getComputedStyle(document.body).fontSize")
            card_title_size = page.evaluate("() => window.getComputedStyle(document.querySelector('.card-title')).fontSize")
            print(f"[+] Увеличенный размер шрифта: {large_font_size} (заголовки: {card_title_size})")

        # Check for horizontal scroll / overflow
        has_horizontal_overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        print(f"[*] Горизонтальный скролл (overflow): {'ОБНАРУЖЕН ПЕРЕЛИВ' if has_horizontal_overflow else 'НЕТ, верстка идеально адаптирована'}")
        
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out_file), full_page=True)
        print(f"[+] Скриншот сохранен: {out_file}")
        
        if console_messages:
            print("[*] Сообщения консоли:")
            for msg in console_messages[:5]:
                print(f"    {msg}")
                
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Playwright Visual Preview & Audit")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL для проверки")
    parser.add_argument("--output", default="preview_desktop.png", help="Путь для скриншота")
    parser.add_argument("--mobile", action="store_true", help="Сделать мобильный снимок")
    parser.add_argument("--toggle-large-font", action="store_true", help="Включить крупный шрифт")
    args = parser.parse_args()
    
    inspect_page(args.url, args.output, args.mobile, args.toggle_large_font)

