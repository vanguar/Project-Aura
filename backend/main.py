import os
import platform
import subprocess
import urllib.parse
import time
import logging
import threading
import mimetypes
import requests as http_requests
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from thefuzz import fuzz
from transliterate import translit
from pydantic import BaseModel

# === ІМПОРТ AI-ПОМІЧНИКА ===
from ai_assistant import assistant as ai_bot

# === НАЛАШТУВАННЯ ЛОГІВ ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AURA_DEBUG")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
TTS_AUDIO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aura_tts.mp3")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def speak_openai_tts(text):
    """Озвучити текст через OpenAI TTS API з retry при 401"""
    api_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)

    for attempt in range(3):
        try:
            response = http_requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": "nova",
                    "response_format": "mp3"
                },
                timeout=30
            )

            if response.status_code == 200:
                with open(TTS_AUDIO_FILE, "wb") as f:
                    f.write(response.content)
                subprocess.run(['termux-media-player', 'play', TTS_AUDIO_FILE],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            elif response.status_code in (401, 403, 429):
                logger.warning(f"TTS {response.status_code} (спроба {attempt+1}/3)")
                api_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
                time.sleep(3)
                continue
            else:
                response.raise_for_status()

        except Exception as e:
            logger.warning(f"TTS помилка (спроба {attempt+1}/3): {e}")
            if attempt < 2:
                time.sleep(2)
                continue

    # Fallback
    try:
        subprocess.Popen(
            ['termux-tts-speak', '-l', 'uk-UA', '-r', '0.85', text[:300]],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except:
        pass

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

⚠️ ВАЖЛИВО: Леводопу Retard о 22:00 ковтати тільки цілою!
"""

MEDS_TIMETABLE = [
    {"time": "05:00", "msg": "Мадопар мікстура, одна доза"},
    {"time": "08:00", "msg": "Леводопа половина таблетки, Ксадаго одна таблетка та Габапентін одна капсула"},
    {"time": "11:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "13:00", "msg": "Габапентін, одна капсула"},
    {"time": "14:00", "msg": "Леводопа, половина таблетки"},
    {"time": "17:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "19:00", "msg": "Габапентін одна капсула та Кветіапін одна таблетка"},
    {"time": "20:00", "msg": "Леводопа, половина таблетки"},
    {"time": "22:00", "msg": "Леводопа Ретард ціла таблетка. Не ламати. Та Кветіапін одна таблетка"}
]

# --- ФОНОВИЙ ПОТІК ---
def check_meds_worker():
    global reminders_enabled, test_active, test_trigger_time
    logger.info("⚙️ Фоновий потік AURA запущено")
    while True:
        now_ts = time.time()
        
        if test_active and now_ts >= test_trigger_time:
            subprocess.run(['termux-notification', '--title', 'ТЕСТ АУРА', '--content', 'Система справна.'])
            subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '1.0', 'Перевірка успішна. Аура працює нормально.'])
            test_active = False
        
        if reminders_enabled:
            current_hm = datetime.now().strftime("%H:%M")
            for item in MEDS_TIMETABLE:
                if item["time"] == current_hm:
                    logger.info(f"🔔 ПРИЙОМ ЛІКІВ: {item['time']}")
                    subprocess.run(['termux-notification', '--title', 'ПРИЙОМ ЛІКІВ', '--content', item['msg']])
                    voice_text = f"Мамо, час приймати ліки. {item['msg']}"
                    subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '0.8', voice_text])
                    time.sleep(61)
        
        time.sleep(1)

threading.Thread(target=check_meds_worker, daemon=True).start()

# ============================================================
# ЕНДПОІНТИ ЛІКІВ (існуючі)
# ============================================================

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

# ============================================================
# ЕНДПОІНТИ AI-ПОМІЧНИКА (оновлені)
# ============================================================

class ChatMessage(BaseModel):
    message: str

@app.post("/ai-chat")
async def ai_chat(body: ChatMessage):
    """Основний ендпоінт чату з AI"""
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Порожнє повідомлення")
    
    result = ai_bot.chat(body.message)
    
    # Озвучення відповіді через OpenAI TTS
    try:
        tts_text = result["reply"][:1500]
        threading.Thread(
            target=speak_openai_tts, args=(tts_text,), daemon=True
        ).start()
    except Exception as e:
        logger.warning(f"TTS помилка: {e}")
    
    return result

@app.post("/ai-chat/doctor-mode")
async def ai_doctor_mode():
    """Переключити на режим лікаря (німецька)"""
    ai_bot.set_doctor_mode()
    return {
        "status": "doctor_mode",
        "message": "Arztmodus aktiviert. Ich kenne die vollständige Krankengeschichte der Patientin und kann Ihnen alle Informationen bereitstellen."
    }

@app.post("/ai-chat/normal-mode")
async def ai_normal_mode():
    """Повернути звичайний режим (українська) + резюме від лікаря"""
    doctor_summary = ai_bot.set_normal_mode()
    return {
        "status": "normal_mode",
        "message": doctor_summary
    }

@app.get("/ai-chat/history")
async def ai_chat_history():
    """Отримати історію діалогу"""
    return ai_bot.get_history()

@app.post("/ai-chat/clear")
async def ai_chat_clear():
    """Очистити історію діалогу"""
    ai_bot.clear_history()
    return {"status": "cleared"}

# ============================================================
# ЕНДПОІНТ БАЛАНСУ OpenAI
# ============================================================

@app.get("/billing/balance")
async def get_billing_balance():
    """Отримати витрати OpenAI через Admin API"""
    admin_key = os.environ.get("OPENAI_ADMIN_KEY", "")
    if not admin_key:
        return {"error": "No admin key", "balance": None}
    try:
        headers = {
            "Authorization": f"Bearer {admin_key}",
            "Content-Type": "application/json"
        }
        start_month = int(time.time()) - (30 * 24 * 60 * 60)
        r = http_requests.get(
            f"https://api.openai.com/v1/organization/costs?start_time={start_month}&bucket_width=1d&limit=31",
            headers=headers, timeout=10
        )
        if r.status_code == 200:
            total = 0.0
            for bucket in r.json().get("data", []):
                for result in bucket.get("results", []):
                    total += float(result.get("amount", {}).get("value", 0))
            return {"balance": {"month": round(total, 2)}}
        else:
            return {"balance": {"api_error": r.status_code}}
    except Exception as e:
        logger.warning(f"Billing error: {e}")
        return {"error": str(e), "balance": None}

# ============================================================
# ЕНДПОІНТИ ПЕРЕКЛАДАЧА
# ============================================================

@app.post("/translator/start")
async def translator_start():
    """Увімкнути режим перекладача"""
    ai_bot.start_translator()
    return {"status": "translator_active"}

@app.post("/translator/stop")
async def translator_stop():
    """Зупинити режим перекладача та отримати звіт"""
    messages = ai_bot.stop_translator()
    return {"status": "translator_stopped", "messages": messages}

class TranslatorMessage(BaseModel):
    text: str
    who: str  # "doctor" або "mama"

@app.post("/translator/translate")
async def translator_translate(body: TranslatorMessage):
    """Переклад повідомлення"""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Порожнє повідомлення")

    if body.who == "doctor":
        translation = ai_bot.translate_doctor(body.text)
        tts_lang_text = translation  # Озвучуємо переклад для мами
    else:
        translation = ai_bot.translate_mama(body.text)
        tts_lang_text = translation  # Озвучуємо переклад для лікаря

    # Озвучення перекладу через OpenAI TTS
    try:
        threading.Thread(
            target=speak_openai_tts, args=(tts_lang_text,), daemon=True
        ).start()
    except Exception as e:
        logger.warning(f"TTS помилка: {e}")

    return {
        "original": body.text,
        "translation": translation,
        "who": body.who
    }

# ============================================================
# ЛОГІКА ПОШУКУ ТА СТРІМІНГУ ВІДЕО (існуюча)
# ============================================================

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
    except Exception as e:
        logger.error(f"Помилка пошуку дисків: {e}")
    return roots

def open_file_http(file_path):
    try:
        subprocess.run(['am', 'force-stop', 'org.videolan.vlc'], stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        encoded_path = urllib.parse.quote(file_path)
        ts = int(time.time())
        stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}&t={ts}"
        subprocess.run(['termux-open', stream_url, '--content-type', 'video/*'])
        return True
    except Exception as e:
        logger.error(f"Помилка запуску файлу: {e}")
        return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Android', 'LOST.DIR', '.thumbnails', 'Data', 'Telegram', 'Backups'}
    search_paths = get_search_roots()
    
    for root_dir in search_paths:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                    video_library.append({
                        "name": file.lower(), 
                        "path": os.path.join(root, file)
                    })
    return video_library

@app.get("/video-stream")
async def video_stream(path: str, request: Request):
    decoded_path = urllib.parse.unquote(path)
    if not os.path.exists(decoded_path): raise HTTPException(status_code=404)
    
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
                    data = f.read(min(1048576, remaining))
                    if not data: break
                    yield data
                    remaining -= len(data)
                    
        return StreamingResponse(iterfile(), status_code=206, media_type=mime_type, headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size)
        })
        
    return StreamingResponse(open(decoded_path, "rb"), media_type=mime_type)

@app.get("/search-movie")
async def search_movie(query: str):
    if not query: return {"found": False}
    
    clean_query = query.lower().replace("запусти", "").replace("фільм", "").replace("фильм", "").strip()
    
    variants = [clean_query]
    try:
        variants.append(translit(clean_query, 'ru', reversed=True))
    except:
        pass
        
    videos = get_all_videos()
    best_match, highest_score = None, 0
    
    for video in videos:
        file_display_name = os.path.splitext(video["name"])[0]
        
        for var in variants:
            score = fuzz.WRatio(var, file_display_name)
            if score > highest_score:
                highest_score = score
                best_match = video
                
    if best_match and highest_score >= 60:
        logger.info(f"🎯 Фільм знайдено ({highest_score}%): {best_match['name']}")
        success = open_file_http(best_match['path'])
        return {"found": success, "filename": os.path.basename(best_match['path']), "score": highest_score}
        
    logger.info(f"🔍 Нічого не знайдено для '{clean_query}'. Найкращий результат: {highest_score}%")
    return {"found": False}

@app.get("/")
async def root():
    return {"status": "ONLINE", "project": "AURA", "ai_mode": ai_bot.mode}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)