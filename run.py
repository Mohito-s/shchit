import os
import socket
import sys
from dotenv import load_dotenv
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port: int = 8000, candidates=(8000, 8001, 8002, 8080, 8888, 5050)) -> int:
    print("[*] Сканирование портов для исключения конфликтов...")
    for port in candidates:
        busy = is_port_in_use(port)
        status = "ЗАНЯТ другим процессом" if busy else "СВОБОДЕН"
        print(f"    - Порт {port}: {status}")
        if not busy:
            return port
    for port in range(start_port + 10, start_port + 100):
        if not is_port_in_use(port):
            return port
    return start_port

if __name__ == "__main__":
    specified_port = os.getenv("PORT")
    if specified_port and specified_port.isdigit():
        port = int(specified_port)
        if is_port_in_use(port):
            print(f"[!] Заданный в .env порт {port} уже занят!")
            port = find_available_port(start_port=port + 1)
            print(f"[+] Переключено на свободный порт: {port}")
    else:
        port = find_available_port(8000)

    print("==================================================")
    print(f"  [+] Запуск сервера «ЩИТ» на порту: {port}")
    print(f"  [+] Адрес в браузере: http://127.0.0.1:{port}")
    print(f"  [+] Swagger документация: http://127.0.0.1:{port}/docs")
    print("==================================================")
    
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=True)


