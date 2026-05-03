import os
import json
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
from typing import Optional
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
    """Озвучити текст через OpenAI TTS API з підтримкою довгих текстів"""
    api_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
    
    # Розбиваємо на чанки по ~3500 символів (по реченнях)
    chunks = split_text_for_tts(text)
    
    for chunk in chunks:
        success = False
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
                        "input": chunk,
                        "voice": "nova",
                        "response_format": "mp3"
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    with open(TTS_AUDIO_FILE, "wb") as f:
                        f.write(response.content)
                    # play і ЧЕКАТИ завершення перед наступним чанком
                    subprocess.run(['termux-media-player', 'play', TTS_AUDIO_FILE],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    # Чекаємо приблизну тривалість аудіо
                    wait_for_playback(len(chunk))
                    success = True
                    break
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

        if not success:
            # Fallback на termux-tts для этого чанка
            try:
                subprocess.run(
                    ['termux-tts-speak', '-l', 'uk-UA', '-r', '0.85', chunk],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except:
                pass


def split_text_for_tts(text, max_len=3500):
    """Розбити текст на чанки по реченнях, не більше max_len символів"""
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    current = ""
    
    # Розбиваємо по реченнях (., !, ?, \n)
    import re
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_len:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # Якщо одне речення довше max_len — обрізаємо
            current = sentence[:max_len]
    
    if current:
        chunks.append(current)
    
    return chunks if chunks else [text[:max_len]]


def wait_for_playback(char_count):
    """Приблизне очікування завершення відтворення"""
    # ~150 символів/сек для TTS
    estimated_seconds = max(char_count / 150, 2)
    time.sleep(estimated_seconds)

# --- СТАН ТА ФАЙЛИ ---
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(_BACKEND_DIR, "state.json")
LAST_FIRED_FILE = os.path.join(_BACKEND_DIR, "last_fired.json")

def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"reminders_enabled": True}

def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"❌ Помилка збереження стану: {e}")

def _load_last_fired() -> dict:
    try:
        with open(LAST_FIRED_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_last_fired(state: dict) -> None:
    try:
        with open(LAST_FIRED_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"❌ Помилка збереження last_fired: {e}")

def _minutes_now() -> int:
    now = datetime.now()
    return now.hour * 60 + now.minute

def _slot_minutes(slot_str: str) -> int:
    h, m = map(int, slot_str.split(":"))
    return h * 60 + m

def _yesterday_iso() -> str:
    from datetime import timedelta
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# --- ГЛОБАЛЬНІ ЗМІННІ ДЛЯ ЛІКІВ ---
_state = _load_state()
reminders_enabled = _state.get("reminders_enabled", True)
test_active = False
test_trigger_time = 0

GRACE_WINDOW_MIN = 15

MEDS_TEXT_SCHEDULE = """
💊 ЩОДЕННИЙ РОЗКЛАД ПРИЙОМУ ЛІКІВ:

🌅 05:00 — Мадопар LT (мікстура) — 1 пакетик
🌄 08:00 — Леводопа 200/50 (½ табл.), Габапентин 100 мг (1 капс.), Еналаприл 10 мг (1 табл.), Макрогол (1 пакетик), Панкреатин (1 капс.)
⏰ 11:00 — Леводопа 200/50 (1 таблетка)
🍽️ 13:00 — Габапентин 100 мг (1 капсула), Панкреатин (1 капс.)
🕐 14:00 — Леводопа 200/50 (½ таблетки)
🕔 17:00 — Леводопа 200/50 (1 таблетка)
🌆 19:00 — Габапентин 100 мг (1 капс.), Кветіапін 25 мг (1 табл.), Еналаприл 10 мг (1 табл.), Панкреатин (1 капс.)
🕗 20:00 — Леводопа 200/50 (½ таблетки)
🌙 22:00 — Леводопа Retard (2 табл. НЕ ЛАМАТИ!), Кветіапін 25 мг (1 табл.), Міртазапін 30 мг (1 табл.)

⚠️ ВАЖЛИВО: Леводопу Retard о 22:00 ковтати тільки цілою!

──────────────────────────
🆘 ЗА ПОТРЕБОЮ (тільки якщо потрібно, БЕЗ автонагадувань):
• Домперидон (Мотіліум) 10 мг — за 1 год до їжі, при нудоті
• Езомепразол 20 мг — при печії/болях у шлунку
• Цетиризин 10 мг — при алергії, ввечері
• Лаксанс (краплі) — 10–15 крапель при запорі (якщо Макрогол не допомагає)
"""

MEDS_TIMETABLE = [
    {"time": "05:00", "msg": "Мадопар мікстура, один пакетик"},
    {"time": "08:00", "msg": "Леводопа половина таблетки, Габапентін одна капсула, Еналаприл одна таблетка, Макрогол один пакетик та Панкреатин одна капсула"},
    {"time": "11:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "13:00", "msg": "Габапентін одна капсула та Панкреатин одна капсула"},
    {"time": "14:00", "msg": "Леводопа, половина таблетки"},
    {"time": "17:00", "msg": "Леводопа, одна ціла таблетка"},
    {"time": "19:00", "msg": "Габапентін одна капсула, Кветіапін одна таблетка, Еналаприл одна таблетка та Панкреатин одна капсула"},
    {"time": "20:00", "msg": "Леводопа, половина таблетки"},
    {"time": "22:00", "msg": "Леводопа Ретард дві таблетки. Не ламати. Кветіапін одна таблетка та Міртазапін одна таблетка"},
]

# --- ФОНОВИЙ ПОТІК ---
def check_meds_worker():
    global reminders_enabled, test_active, test_trigger_time
    logger.info("⚙️ Фоновий потік AURA запущено")
    last_fired = _load_last_fired()

    while True:
        now_ts = time.time()

        if test_active and now_ts >= test_trigger_time:
            subprocess.run(['termux-notification', '--title', 'ТЕСТ АУРА', '--content', 'Система справна.'])
            subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '1.0', 'Перевірка успішна. Аура працює нормально.'])
            test_active = False

        if reminders_enabled:
            today = datetime.now().strftime("%Y-%m-%d")
            now_min = _minutes_now()

            for item in MEDS_TIMETABLE:
                slot_min = _slot_minutes(item["time"])
                key = f"{today}:{item['time']}"
                if key in last_fired:
                    continue
                delta = now_min - slot_min
                if 0 <= delta <= GRACE_WINDOW_MIN:
                    logger.info(f"🔔 ПРИЙОМ ЛІКІВ ({item['time']}, запізнення {delta} хв)")
                    subprocess.run(['termux-notification', '--title', 'ПРИЙОМ ЛІКІВ', '--content', item['msg']])
                    voice_text = f"Мамо, час приймати ліки. {item['msg']}"
                    subprocess.run(['termux-tts-speak', '-l', 'uk-UA', '-r', '0.8', voice_text])
                    last_fired[key] = now_ts
                    yesterday = _yesterday_iso()
                    last_fired = {k: v for k, v in last_fired.items() if k.startswith(today) or k.startswith(yesterday)}
                    _save_last_fired(last_fired)

        time.sleep(5)

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
    _save_state({"reminders_enabled": True})
    return {"status": "enabled"}

@app.post("/disable-reminders")
async def disable_reminders():
    global reminders_enabled, test_active
    reminders_enabled = False
    test_active = False
    _save_state({"reminders_enabled": False})
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
        tts_text = result["reply"]
        threading.Thread(
            target=speak_openai_tts, args=(tts_text,), daemon=True
        ).start()
    except Exception as e:
        logger.warning(f"TTS помилка: {e}")
    
    return result

class DoctorModeRequest(BaseModel):
    lang: str = "de"  # "de" або "uk"

@app.post("/ai-chat/doctor-mode")
async def ai_doctor_mode(body: Optional[DoctorModeRequest] = None):
    """Переключити на режим лікаря. lang: 'de' (Німеччина) або 'uk' (Україна)."""
    lang = body.lang if (body and body.lang in ("de", "uk")) else "de"
    ai_bot.set_doctor_mode(lang=lang)
    if lang == "uk":
        message = "Режим лікаря активовано. Я знаю повну медичну історію пацієнтки і готова надати інформацію."
    else:
        message = "Arztmodus aktiviert. Ich kenne die vollständige Krankengeschichte der Patientin und kann Ihnen alle Informationen bereitstellen."
    return {"status": "doctor_mode", "lang": lang, "message": message}

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
# ЕНДПОІНТИ SOS
# ============================================================

@app.post("/sos/alert")
async def sos_alert():
    """Миттєве SOS-сповіщення в Telegram"""
    try:
        ai_bot.send_sos_alert()
        return {"status": "sent", "message": "SOS alert sent to Telegram"}
    except Exception as e:
        logger.error(f"SOS alert error: {e}")
        return {"status": "error", "message": str(e)}

class SOSVoice(BaseModel):
    text: str

@app.post("/sos/details")
async def sos_details(body: SOSVoice):
    """AI інтерпретує голосове повідомлення SOS і відправляє в Telegram"""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Порожнє повідомлення")
    
    try:
        interpretation = ai_bot.interpret_sos_voice(body.text)
        return {"status": "sent", "interpretation": interpretation}
    except Exception as e:
        logger.error(f"SOS details error: {e}")
        return {"status": "error", "message": str(e)}

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
    """Переклад повідомлення (AI-інтерпретація + дослівний)"""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Порожнє повідомлення")

    if body.who == "doctor":
        result = ai_bot.translate_doctor(body.text)
    else:
        result = ai_bot.translate_mama(body.text)

    ai_translation = result["ai"]
    literal_translation = result["literal"]

    # Озвучення AI-перекладу через OpenAI TTS
    try:
        threading.Thread(
            target=speak_openai_tts, args=(ai_translation,), daemon=True
        ).start()
    except Exception as e:
        logger.warning(f"TTS помилка: {e}")

    return {
        "original": body.text,
        "translation": ai_translation,
        "literal": literal_translation,
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