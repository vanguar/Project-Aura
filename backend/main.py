import os
import platform
import subprocess
import urllib.parse
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from thefuzz import fuzz
from transliterate import translit

# === НАСТРОЙКИ ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Поддерживаемые форматы
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'}

# === 1. ГДЕ ИСКАТЬ ФАЙЛЫ ===
def get_search_roots():
    roots = []
    if platform.system() == "Windows":
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive): roots.append(drive)
    else:
        # Пути для Android (Termux)
        paths = [
            '/storage/emulated/0/Movies/',
            '/storage/emulated/0/Download/',
            '/storage/emulated/0/DCIM/',   # Камера
            '/storage/emulated/0/Video/',
            '/storage/emulated/0/'         # Корень (на всякий случай)
        ]
        for p in paths:
            if os.path.exists(p): roots.append(p)
    return roots

SEARCH_ROOTS = get_search_roots()

# === 2. ЛОГИКА ЗАПУСКА (HTTP STREAM) ===
def open_file_http(file_path):
    """
    Запускает локальный стрим, чтобы обойти политику безопасности Android.
    VLC думает, что играет видео из интернета.
    """
    try:
        # 1. Кодируем путь (пробелы -> %20 и т.д.)
        encoded_path = urllib.parse.quote(file_path)
        
        # 2. Создаем ссылку на самих себя
        stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}"
        
        print(f"🚀 [ЗАПУСК] Файл: {os.path.basename(file_path)}")
        print(f"🔗 [ССЫЛКА] {stream_url}")
        
        # 3. МАГИЧЕСКАЯ ПАУЗА (Fix для слабых процессоров)
        time.sleep(0.3)
        
        # 4. Открываем через termux-open
        # Флаг --choose вызовет меню выбора плеера (выбери VLC!)
        subprocess.run([
            'termux-open', 
            stream_url, 
            '--choose',
            '--content-type', 'video/*'
        ])
        return True
    except Exception as e:
        print(f"⚠️ Ошибка запуска: {e}")
        return False

def open_file(file_path):
    # Если это Windows (тест на ПК)
    if platform.system() == "Windows":
        os.startfile(file_path)
        return True
    # Если это Android
    else:
        return open_file_http(file_path)

# === 3. ПОИСК ФАЙЛОВ ===
def get_all_videos():
    video_library = []
    # Папки, которые мы игнорируем, чтобы не тормозить
    exclude_dirs = {'Android', 'LOST.DIR', '.thumbnails', 'Data', 'Telegram', 'Backups'}
    
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        full_path = os.path.join(root, file)
                        video_library.append({"name": file.lower(), "path": full_path})
    return video_library

# === 4. СЕРВЕР СТРИМИНГА (Эмуляция YouTube) ===
@app.get("/video-stream")
async def video_stream(path: str, request: Request):
    # Декодируем путь обратно
    decoded_path = urllib.parse.unquote(path)
    
    if not os.path.exists(decoded_path):
        print(f"❌ Стрим невозможен, файл не найден: {decoded_path}")
        return {"error": "File not found"}
        
    file_size = os.path.getsize(decoded_path)
    range_header = request.headers.get("range")
    
    # MIME тип (VLC всеяден, mp4 универсален)
    media_type = "video/mp4"

    # Обработка перемотки (Range requests)
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
                    # Читаем по 64 КБ
                    read_size = min(65536, remaining)
                    data = f.read(read_size)
                    if not data: break
                    yield data
                    remaining -= len(data)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        }
        return StreamingResponse(
            iterfile(), 
            status_code=206, 
            media_type=media_type, 
            headers=headers
        )
    
    # Если запросили файл целиком (редко)
    return StreamingResponse(
        open(decoded_path, "rb"), 
        media_type=media_type
    )

# === 5. API ENDPOINTS ===
@app.get("/")
async def root():
    videos = get_all_videos()
    return {
        "status": "Aura Streaming Server v3.0", 
        "ready": True,
        "videos_found": len(videos)
    }

@app.get("/search-movie")
async def search_movie(query: str):
    print(f"🔎 Голосовой запрос: '{query}'")
    try:
        if not query: return {"found": False}
        
        # Очистка запроса
        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        variants = [clean_query]
        try: variants.append(translit(clean_query, 'ru', reversed=True))
        except: pass

        videos = get_all_videos()
        best_match = None
        highest_score = 0
        
        # Нечеткий поиск
        for video in videos:
            for var in variants:
                # token_set_ratio лучше справляется с перестановкой слов
                score = fuzz.token_set_ratio(var, video["name"])
                if score > highest_score:
                    highest_score = score
                    best_match = video

        print(f"📊 Найдено: {highest_score}% -> {best_match['name'] if best_match else 'Пусто'}")

        if best_match and highest_score > 60:
            success = open_file(best_match['path'])
            return {
                "found": success, 
                "filename": os.path.basename(best_match['path']),
                "score": highest_score
            }
        
        return {"found": False}
    except Exception as e:
        print(f"☢️ Критическая ошибка: {e}")
        return {"found": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Запуск на всех интерфейсах
    uvicorn.run(app, host="0.0.0.0", port=8000)