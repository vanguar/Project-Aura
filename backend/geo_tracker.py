import subprocess
import time
import json
import logging
import requests

# --- ВАШИ ДАННЫЕ (Оставлены без изменений) ---
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

def get_location_data(provider):
    """Попытка получить данные от конкретного провайдера"""
    try:
        # -r last: брать последние известные (быстро)
        cmd = ["termux-location", "-p", provider, "-r", "last"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                # ГЛАВНОЕ ИСПРАВЛЕНИЕ: Проверяем, есть ли ключи, прежде чем читать
                if "latitude" in data and "longitude" in data:
                    return data["latitude"], data["longitude"]
            except json.JSONDecodeError:
                pass
        return None, None
    except Exception as e:
        logging.error(f"Ошибка провайдера {provider}: {e}")
        return None, None

def get_location():
    """Умный поиск: сначала Сеть, если пусто — тогда GPS"""
    # 1. Пробуем Network (быстро, бережет батарею)
    lat, lon = get_location_data("network")
    if lat:
        return lat, lon
    
    # 2. Если Network пусто — пробуем GPS (точнее, но медленнее)
    logging.info("Network пусто, пробую GPS...")
    lat, lon = get_location_data("gps")
    return lat, lon

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
    # Сообщение о запуске
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
            logging.info(f"Координаты отправлены: {lat}, {long}")
        else:
            logging.warning("Не удалось получить координаты (и Network, и GPS молчат)")
        
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()