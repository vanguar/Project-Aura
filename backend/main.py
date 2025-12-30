import os
import platform
import subprocess
import urllib.parse
import time
import logging
import threading
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from thefuzz import fuzz
from transliterate import translit

# === НАСТРОЙКА ЛОГОВ (ЧЕРНЫЙ ЯЩИК) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AURA_DEBUG")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- БЛОК: ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ ЛЕКАРСТВ ---
reminders_enabled = False
test_triggered = False  # Флаг, что тест уже был проведен
test_deadline = 0       # Время срабатывания теста

# Полный текст графика для экрана мамы
MEDS_TEXT_SCHEDULE = """
💊 ЩОДЕННИЙ РОЗКЛАД ПРИЙОМУ ЛІКІВ:

🌅 05:00 — Мадопар LT (мікстура) — 1 доза
🌄 08:00 — Леводопа/Карбідопа 200/50 (½ табл.), Ксадаго 50 мг (1 табл.), Габапентин 100 мг (1 капс.)
⏰ 11:00 — Леводопа/Карбідопа 200/50 (1 таблетка)
🍽️ 13:00 — Габапентин 100 мг (1 капсула)
🕐 14:00 — Леводопа/Карбідопа 200/50 (½ таблетки)
🕔 17:00 — Леводопа/Карбідопа 200/50 (1 таблетка)
🌆 19:00 — Габапентин 100 мг (1 капсула), Кветіапін 25 мг (1 табл.)
🕗 20:00 — Леводопа/Карбідопа 200/50 (½ таблетки)
🌙 22:00 — Леводопа Retard 100/25 (1 табл. НЕ ЛАМАТИ!), Кветіапін 25 мг (1 табл.)

⚠️ ВАЖЛИВО: Леводопу Retard о 22:00 ковтати тільки цілою!
"""

# Список для логики уведомлений
MEDS_TIMETABLE = [
    {"time": "05:00", "msg": "Мадопар мікстура, одна доза"},
    {"time": "08:00", "msg": "Леводопа пів-таблетки, Ксадаго одна таблетка та Габапентин одна капсула"},
    {"time": "11:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "13:00", "msg": "Габапентин, одна капсула"},
    {"time": "14:00", "msg": "Леводопа, пів-таблетки"},
    {"time": "17:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "19:00", "msg": "Габапентин одна капсула та Кветіапін одна таблетка"},
    {"time": "20:00", "msg": "Леводопа, пів-таблетки"},
    {"time": "22:00", "msg": "Увага! Леводопа Ретард ціла таблетка. Не ламати! Та Кветіапін одна таблетка"}
]

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'}

def get_search_roots():
    roots = []
    if platform.system() == "Windows":
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive): roots.append(drive)
    else:
        paths = ['/storage/emulated/0/Movies/', '/storage/emulated/0/Download/', '/storage/emulated/0/DCIM/', '/storage/emulated/0/']
        for p in paths:
            if os.path.exists(p): 
                roots.append(p)
                logger.info(f"📂 Папка доступна: {p}")
    return roots

SEARCH_ROOTS = get_search_roots()

# --- ФОНОВЫЙ ПОТОК: ТЕСТ + ШТАТНЫЙ РЕЖИМ ---
def check_meds_worker():
    global reminders_enabled, test_triggered, test_deadline
    logger.info("⚙️ Фоновий потік АУРА запущено")
    while True:
        if reminders_enabled:
            # 1. Логика ТЕСТА (срабатывает один раз через 30 сек)
            if not test_triggered:
                if time.time() >= test_deadline:
                    logger.info("🧪 ТЕСТ СИСТЕМИ: Сигнал через 30 секунд")
                    subprocess.run(['termux-notification', '--title', 'ТЕСТ АУРА', '--content', 'Перевірка успішна. Система перейшла в робочий режим.', '--priority', 'high'])
                    subprocess.run(['termux-tts-speak', 'Тестова перевірка успішна. Система Аура працює. Я стежу за розкладом ліків.'])
                    test_triggered = True
            
            # 2. Штатный режим мониторинга расписания
            current_time = datetime.now().strftime("%H:%M")
            for item in MEDS_TIMETABLE:
                if item["time"] == current_time:
                    logger.info(f"🔔 РОБОЧИЙ СИГНАЛ: {item['time']}")
                    subprocess.run(['termux-notification', '--title', 'ПРИЙОМ ЛІКІВ', '--content', item['msg'], '--priority', 'high'])
                    voice_text = f"Мама, пора приймати ліки. {item['msg']}"
                    subprocess.run(['termux-tts-speak', voice_text])
                    time.sleep(61) # Пауза, чтобы не дублировать в ту же минуту
        
        time.sleep(5) # Проверка каждые 5 секунд для точности теста

threading.Thread(target=check_meds_worker, daemon=True).start()

# --- ЭНДПОИНТЫ УПРАВЛЕНИЯ ---
@app.get("/get-meds-schedule")
async def get_meds_schedule():
    return {"schedule": MEDS_TEXT_SCHEDULE, "enabled": reminders_enabled}

@app.post("/enable-reminders")
async def enable_reminders():
    global reminders_enabled, test_triggered, test_deadline
    reminders_enabled = True
    test_triggered = False # Сбрасываем флаг для нового теста
    test_deadline = time.time() + 30 # Установка теста на через 30 секунд
    logger.info("🚀 Активація системи: Тест через 30с запущен")
    return {"status": "enabled"}

@app.post("/disable-reminders")
async def disable_reminders():
    global reminders_enabled
    reminders_enabled = False
    logger.info("⛔ Система вимкнена користувачем")
    return {"status": "disabled"}

# --- ОРИГИНАЛЬНЫЙ БЛОК: УПРАВЛЕНИЕ ВИДЕО ---
def open_file_http(file_path):
    try:
        encoded_path = urllib.parse.quote(file_path)
        stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}"
        logger.info(f"🚀 [CMD] Открываю: {stream_url}")
        time.sleep(0.5)
        subprocess.run(['termux-open', stream_url, '--choose', '--content-type', 'video/*'], capture_output=True, text=True)
        return True
    except Exception as e:
        logger.error(f"☢️ Ошибка subprocess: {e}")
        return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Android', 'LOST.DIR', '.thumbnails', 'Data', 'Telegram', 'Backups'}
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        video_library.append({"name": file.lower(), "path": os.path.join(root, file)})
    return video_library

@app.get("/video-stream")
async def video_stream(path: str, request: Request):
    decoded_path = urllib.parse.unquote(path)
    if not os.path.exists(decoded_path): return {"error": "File not found"}
    file_size = os.path.getsize(decoded_path)
    range_header = request.headers.get("range")
    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        chunk_size = (end - start) + 1
        def iterfile():
            with open(decoded_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = f.read(min(65536, remaining))
                    if not data: break
                    yield data
                    remaining -= len(data)
        return StreamingResponse(iterfile(), status_code=206, media_type="video/mp4", headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes", "Content-Length": str(chunk_size),
        })
    return StreamingResponse(open(decoded_path, "rb"), media_type="video/mp4")

@app.get("/search-movie")
async def search_movie(query: str):
    try:
        if not query: return {"found": False}
        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        variants = [clean_query]
        try: variants.append(translit(clean_query, 'ru', reversed=True))
        except: pass
        videos = get_all_videos()
        best_match, highest_score = None, 0
        for video in videos:
            for var in variants:
                score = fuzz.token_set_ratio(var, video["name"])
                if score > highest_score: highest_score, best_match = score, video
        if best_match and highest_score > 60:
            success = open_file_http(best_match['path'])
            return {"found": success, "filename": os.path.basename(best_match['path'])}
        return {"found": False}
    except Exception as e:
        logger.error(f"☢️ Ошибка поиска: {e}")
        return {"found": False}

@app.get("/")
async def root():
    return {"status": "AURA ONLINE", "ready": True, "reminders_active": reminders_enabled}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)