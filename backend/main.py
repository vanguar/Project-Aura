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

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ЛЕКАРСТВ ---
reminders_enabled = False
test_active = False
test_trigger_time = 0

MEDS_TEXT_SCHEDULE = """
💊 ЩОДЕННИЙ РОЗКЛАД ПРИЙОМУ ЛІКІВ:

🌅 05:00 — Мадопар LT (мікстура) — 1 доза
🌄 08:00 — Леводопа 200/50 (½ табл.), Ксадаго 50 мг (1 табл.), Габапентин 100 мг (1 капс.)
⏰ 11:00 — Леводопа 200/50 (1 таблетка)
🍽️ 13:00 — Габапентин 100 мг (1 капсула)
🕐 14:00 — Леводопа 200/50 (½ таблетки)
🕔 17:00 — Леводопа 200/50 (1 таблетка)
🌆 19:00 — Габапентин 100 мг (1 капсула), Кветіапін 25 мг (1 табл.)
🕗 20:00 — Леводопа 200/50 (½ таблетки)
🌙 22:00 — Леводопа Retard (1 табл. НЕ ЛАМАТИ!), Кветіапін 25 мг (1 табл.)

⚠️ ВАЖЛИВО: Леводопу Retard о 22:00 ковтати тільки цілою!
"""

MEDS_TIMETABLE = [
    {"time": "05:00", "msg": "Мадопар мікстура, одна доза"},
    {"time": "08:00", "msg": "Леводопа пів-таблетки, Ксадаго одна таблетка та Габапентин одна капсула"},
    {"time": "11:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "13:00", "msg": "Габапентин, одна капсула"},
    {"time": "14:00", "msg": "Леводопа, пів-таблетки"},
    {"time": "17:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "19:00", "msg": "Габапентин одна капсула та Кветіапін одна таблетка"},
    {"time": "20:00", "msg": "Леводопа, пів-таблетки"},
    {"time": "22:00", "msg": "Увага! Леводопа Ретард ціла таблетка. Не ламати. Та Кветіапін одна таблетка"}
]

# --- ОРИГИНАЛЬНЫЙ БЛОК: ПОИСК ФАЙЛОВ ---
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'}

def get_search_roots():
    roots = []
    if platform.system() == "Windows":
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive): roots.append(drive)
    else:
        paths = [
            '/storage/emulated/0/Movies/',
            '/storage/emulated/0/Download/',
            '/storage/emulated/0/DCIM/',
            '/storage/emulated/0/Video/',
            '/storage/emulated/0/' 
        ]
        for p in paths:
            if os.path.exists(p): 
                roots.append(p)
                logger.info(f"📂 Папка доступна: {p}")
    return roots

SEARCH_ROOTS = get_search_roots()

# --- ФОНОВЫЙ ПОТОК (ТЕСТ + МОНИТОРИНГ) ---
def check_meds_worker():
    global reminders_enabled, test_active, test_trigger_time
    while True:
        now_ts = time.time()
        
        # 1. ТЕСТ СИСТЕМЫ (через 30 секунд после включения)
        if test_active and now_ts >= test_trigger_time:
            subprocess.run(['termux-notification', '--title', 'ТЕСТ АУРА', '--content', 'Система справна. Перевірка голосу та сповіщень успішна.'])
            subprocess.run(['termux-tts-speak', 'Тестове нагадування успішне. Система Аура працює.'])
            test_active = False

        # 2. ШТАТНЫЙ МОНИТОРИНГ
        if reminders_enabled:
            now_hm = datetime.now().strftime("%H:%M")
            for item in MEDS_TIMETABLE:
                if item["time"] == now_hm:
                    subprocess.run(['termux-notification', '--title', 'ПРИЙОМ ЛІКІВ', '--content', item['msg'], '--priority', 'high'])
                    subprocess.run(['termux-tts-speak', f"Мама, час приймати ліки. {item['msg']}"])
                    time.sleep(61)
        
        time.sleep(1)

threading.Thread(target=check_meds_worker, daemon=True).start()

# --- ЭНДПОИНТЫ ДЛЯ ЛЕКАРСТВ ---
@app.get("/get-meds-schedule")
async def get_meds_schedule():
    return {"schedule": MEDS_TEXT_SCHEDULE, "enabled": reminders_enabled}

@app.post("/enable-reminders")
async def enable_reminders():
    global reminders_enabled, test_active, test_trigger_time
    reminders_enabled = True
    test_active = True
    test_trigger_time = time.time() + 30
    return {"status": "enabled"}

@app.post("/disable-reminders")
async def disable_reminders():
    global reminders_enabled, test_active
    reminders_enabled = False
    test_active = False
    return {"status": "disabled"}

# --- ОРИГИНАЛЬНЫЙ БЛОК: СТРИМИНГ И ПОИСК ФИЛЬМОВ ---
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
    media_type = "video/mp4"

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
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            media_type=media_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
            },
        )
    return StreamingResponse(open(decoded_path, "rb"), media_type=media_type)

@app.get("/search-movie")
async def search_movie(query: str):
    logger.info(f"🔎 ПОИСК: '{query}'")
    try:
        if not query: return {"found": False}
        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        variants = [clean_query]
        try: variants.append(translit(clean_query, 'ru', reversed=True))
        except: pass

        videos = get_all_videos()
        best_match = None
        highest_score = 0
        
        for video in videos:
            for var in variants:
                score = fuzz.token_set_ratio(var, video["name"])
                if score > highest_score:
                    highest_score = score
                    best_match = video

        if best_match and highest_score > 60:
            success = open_file_http(best_match['path'])
            return {"found": success, "filename": os.path.basename(best_match['path'])}
        return {"found": False}
    except Exception as e:
        logger.error(f"☢️ Ошибка поиска: {e}")
        return {"found": False}

@app.get("/")
async def root(): return {"status": "ONLINE"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)