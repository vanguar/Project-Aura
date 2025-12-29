import os
import platform
import subprocess
import urllib.parse
import time
import logging
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
            else:
                logger.warning(f"⚠️ Папка НЕ доступна: {p}")
    return roots

SEARCH_ROOTS = get_search_roots()

def open_file_http(file_path):
    try:
        encoded_path = urllib.parse.quote(file_path)
        stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}"
        
        logger.info(f"🚀 [CMD] Пытаюсь открыть ссылку: {stream_url}")
        
        time.sleep(0.5) # Увеличил задержку для теста
        
        # Запускаем и ловим ошибку, если termux-open не сработает
        result = subprocess.run([
            'termux-open', 
            stream_url, 
            '--choose',
            '--content-type', 'video/*'
        ], capture_output=True, text=True)
        
        logger.info(f"📱 Termux output: {result.stdout}")
        if result.stderr:
            logger.error(f"❌ Termux error: {result.stderr}")
            
        return True
    except Exception as e:
        logger.error(f"☢️ CRASH при запуске subprocess: {e}")
        return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Android', 'LOST.DIR', '.thumbnails', 'Data', 'Telegram', 'Backups'}
    
    logger.info("⏳ Начинаю полное сканирование...")
    count = 0
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        full_path = os.path.join(root, file)
                        video_library.append({"name": file.lower(), "path": full_path})
                        count += 1
                        # Логируем только первые 3 файла, чтобы не спамить
                        if count <= 3: logger.info(f"   📄 Найден файл: {file}")
    
    logger.info(f"✅ Всего найдено видео: {count}")
    return video_library

@app.get("/video-stream")
async def video_stream(path: str, request: Request):
    # ЛОГИРУЕМ ВХОДЯЩИЙ ЗАПРОС ОТ ПЛЕЕРА
    logger.info(f"📡 [SERVER] Входящее подключение! Плеер постучался.")
    logger.info(f"   Headers: {request.headers}")
    
    decoded_path = urllib.parse.unquote(path)
    logger.info(f"   Запрошен файл: {decoded_path}")
    
    if not os.path.exists(decoded_path):
        logger.error(f"❌ ФАЙЛ НЕ СУЩЕСТВУЕТ ПО ПУТИ: {decoded_path}")
        return {"error": "File not found"}
        
    file_size = os.path.getsize(decoded_path)
    range_header = request.headers.get("range")
    
    media_type = "video/mp4"

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        chunk_size = (end - start) + 1
        
        logger.info(f"   ⏩ Range запрос: байты {start}-{end} (Размер чанка: {chunk_size})")

        def iterfile():
            try:
                with open(decoded_path, "rb") as f:
                    f.seek(start)
                    remaining = chunk_size
                    while remaining > 0:
                        read_size = min(65536, remaining)
                        data = f.read(read_size)
                        if not data: break
                        yield data
                        remaining -= len(data)
            except Exception as e:
                logger.error(f"   ☢️ Ошибка чтения файла в потоке: {e}")

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        }
        return StreamingResponse(iterfile(), status_code=206, media_type=media_type, headers=headers)
    
    logger.info("   📦 Полная загрузка файла (без Range)")
    return StreamingResponse(open(decoded_path, "rb"), media_type=media_type)

@app.get("/")
async def root():
    return {"status": "DEBUG MODE", "ready": True}

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

        logger.info(f"📊 Результат поиска: {highest_score}% -> {best_match['name'] if best_match else 'Пусто'}")

        if best_match and highest_score > 60:
            success = open_file_http(best_match['path'])
            return {"found": success, "filename": os.path.basename(best_match['path'])}
        
        return {"found": False}
    except Exception as e:
        logger.error(f"☢️ Ошибка в search_movie: {e}")
        return {"found": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # log_level="info" покажет системные логи uvicorn тоже
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")