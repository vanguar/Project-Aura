import os
import platform
import subprocess
import urllib.parse
import time
import logging
import threading
import mimetypes
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from thefuzz import fuzz
from transliterate import translit

# === НАЛАШТУВАННЯ ЛОГІВ ===
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

# --- ГЛОБАЛЬНІ ЗМІННІ ДЛЯ ЛІКІВ ---
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

⚠️ ВАЖЛИВО: Леводопу Retard о 22:00 ковтати только цілою!
"""

MEDS_TIMETABLE = [
    {"time": "05:00", "msg": "МадопАр мікстУра, однА дОза"},
    {"time": "08:00", "msg": "ЛеводОпа половИна таблЕтки, КсадАго однА таблЕтка та ГабапентІн однА кАпсула"},
    {"time": "11:00", "msg": "ЛеводОпа, однА цІла таблЕтка"},
    {"time": "13:00", "msg": "ГабапентІн, однА кАпсула"},
    {"time": "14:00", "msg": "ЛеводОпа, половИна таблЕтки"},
    {"time": "17:00", "msg": "ЛеводОпа, однА цІла таблЕтка"},
    {"time": "19:00", "msg": "ГабапентІн однА кАпсула та КветіапІн однА таблЕтка"},
    {"time": "20:00", "msg": "ЛеводОпа, половИна таблЕтки"},
    {"time": "22:00", "msg": "ЛеводОпа РетАрд цІла таблЕтка. Не ламати. Та КветіапІн однА таблЕтка"}
]

def check_meds_worker():
    global reminders_enabled, test_active, test_trigger_time
    logger.info("⚙️ Фоновий потік АУРА запущено")
    while True:
        now_ts = time.time()
        if test_active and now_ts >= test_trigger_time:
            subprocess.run(['termux-notification', '--title', 'ТЕСТ АУРА', '--content', 'Система справна.'])
            subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '1.0', 'ПеревІрка успішна.'])
            test_active = False
        
        if reminders_enabled:
            current_hm = datetime.now().strftime("%H:%M")
            for item in MEDS_TIMETABLE:
                if item["time"] == current_hm:
                    subprocess.run(['termux-notification', '--title', 'ПРИЙОМ ЛІКІВ', '--content', item['msg']])
                    voice_text = f"Мамо, час приймати ліки. {item['msg']}"
                    subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '0.8', voice_text])
                    time.sleep(61)
        time.sleep(1)

threading.Thread(target=check_meds_worker, daemon=True).start()

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

# --- ПОШУК ТА СТРІМІНГ ---
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'}

def get_search_roots():
    roots = []
    internal_storage = '/storage/emulated/0/'
    if os.path.exists(internal_storage): roots.append(internal_storage)
    try:
        if os.path.exists('/storage/'):
            for item in os.listdir('/storage/'):
                if item not in ['emulated', 'self', 'knox-emulated']:
                    sd_path = os.path.join('/storage/', item)
                    if os.path.isdir(sd_path): roots.append(sd_path)
    except Exception as e: logger.error(f"SD Error: {e}")
    return roots

def open_file_http(file_path):
    try:
        # ВАЖЛИВО: Очищаємо плеєр перед новим запуском
        subprocess.run(['am', 'force-stop', 'org.videolan.vlc'], stderr=subprocess.DEVNULL)
        time.sleep(0.5)

        encoded_path = urllib.parse.quote(file_path)
        # Додаємо timestamp для унікальності URL
        ts = int(time.time())
        stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}&t={ts}"
        subprocess.run(['termux-open', stream_url, '--content-type', 'video/*'])
        return True
    except: return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Android', 'LOST.DIR', '.thumbnails', 'Data', 'Telegram', 'Backups'}
    search_paths = get_search_roots()
    for root_dir in search_paths:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                    video_library.append({"name": file.lower(), "path": os.path.join(root, file)})
    return video_library

@app.get("/video-stream")
async def video_stream(path: str, request: Request):
    decoded_path = urllib.parse.unquote(path)
    if not os.path.exists(decoded_path): return {"error": "File not found"}
    
    # Визначаємо справжній MIME-тип файлу
    mime_type, _ = mimetypes.guess_type(decoded_path)
    mime_type = mime_type or "video/mp4"
    
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
                    # Буфер 1МБ для стабільності
                    data = f.read(min(1048576, remaining))
                    if not data: break
                    yield data
                    remaining -= len(data)
        return StreamingResponse(iterfile(), status_code=206, media_type=mime_type, headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}", 
            "Accept-Ranges": "bytes", 
            "Content-Length": str(chunk_size)})
            
    return StreamingResponse(open(decoded_path, "rb"), media_type=mime_type)

@app.get("/search-movie")
async def search_movie(query: str):
    if not query: return {"found": False}
    clean_query = query.lower().replace("запусти", "").replace("фільм", "").replace("фильм", "").strip()
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

@app.get("/")
async def root(): return {"status": "ONLINE"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)