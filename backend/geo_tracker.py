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
                if "latitude" in data and "longitude" in data:
                    return data["latitude"], data["longitude"], None
            except json.JSONDecodeError:
                return None, None, "Ошибка формата данных"
        
        # Если команда вернула ошибку (например, доступ запрещен)
        error_msg = result.stderr.strip() if result.stderr else "Нет сигнала"
        return None, None, error_msg

    except Exception as e:
        logging.error(f"Ошибка провайдера {provider}: {e}")
        return None, None, str(e)

def get_location():
    """Умный поиск: сначала Сеть, если пусто — тогда GPS"""
    # 1. Пробуем Network
    lat, lon, err_net = get_location_data("network")
    if lat:
        return lat, lon, None
    
    # 2. Если Network пусто — пробуем GPS
    logging.info("Network пусто, пробую GPS...")
    lat, lon, err_gps = get_location_data("gps")
    
    # Собираем ошибку, если оба провайдера молчат
    final_error = f"Network: {err_net} | GPS: {err_gps}"
    return lat, lon, final_error

def send_to_telegram(lat, long):
    try:
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{long}"
        message = f"📍 <b>Геолокация Aura</b>\n{maps_link}"
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Ошибка сети: {e}")

def send_error_to_tg(error_text):
    """Отправка текста ошибки прямо в канал"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": f"⚠️ <b>Ошибка GPS:</b> {error_text}", "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def send_sos_alert_geo():
    """SOS-ескалація: 20+ хвилин без координат"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": "🚨 <b>Не можу знайти маму понад 20 хвилин.</b>\nПеревір її стан.",
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def main():
    # Сообщение о запуске
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": "🛰️ Aura Tracker: Мониторинг запущен"}
        )
    except:
        pass

    fail_streak = 0
    ESCALATION_THRESHOLD = 4  # 4 цикли × 5 хв = 20 хвилин

    while True:
        lat, long, error = get_location()

        if lat and long:
            if fail_streak >= ESCALATION_THRESHOLD:
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={"chat_id": CHAT_ID, "text": "✅ Координати знову приходять", "parse_mode": "HTML"},
                        timeout=10
                    )
                except:
                    pass
            fail_streak = 0
            send_to_telegram(lat, long)
            logging.info(f"Координаты отправлены: {lat}, {long}")
        else:
            fail_streak += 1
            logging.warning(f"Сбой #{fail_streak}: {error}")
            if fail_streak == 1:
                send_error_to_tg(error)
            elif fail_streak == ESCALATION_THRESHOLD:
                send_sos_alert_geo()

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()