import subprocess
import json
import requests
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"
CHAT_ID = "ВАШ_ID_КАНАЛА" # Например: -100123456789
INTERVAL = 600 # 10 минут
# ---------------------

def get_location():
    try:
        # Получение GPS данных через Termux API
        result = subprocess.run(
            ["termux-location", "-p", "gps"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Ошибка получения локации: {e}")
    return None

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False # Чтобы карта подгружалась превью
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def main():
    print("Фоновый мониторинг Ауры запущен...")
    while True:
        data = get_location()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if data:
            lat = data.get("latitude")
            lon = data.get("longitude")
            
            # Полная ссылка на Google Карты с маркером
            google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            
            message = (
                f"🔘 *Отчет системы Аура*\n"
                f"⏰ Время: {current_time}\n"
                f"📍 Координаты: `{lat}, {lon}`\n\n"
                f"🗺 *Местоположение на карте:*\n"
                f"{google_maps_link}"
            )
            send_to_telegram(message)
        else:
            send_to_telegram(f"⚠️ {current_time}: Не удалось получить GPS-сигнал.")
            
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()