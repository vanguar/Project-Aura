from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import platform
import string 
import urllib.parse
import subprocess
from thefuzz import fuzz
from transliterate import translit

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v'}

def get_search_roots():
    roots = []
    if platform.system() == "Windows":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append(drive)
    else:
        # Приоритет для Android
        paths = ['/storage/emulated/0/Movies/Aura/', '/storage/emulated/0/Download/']
        for p in paths:
            if os.path.exists(p):
                roots.append(p)
    return roots

SEARCH_ROOTS = get_search_roots()

def open_file(file_path):
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        else:
            # СОВЕТ ДРУГОЙ НЕЙРОНКИ + МОЙ ФИКС:
            # Кодируем путь для URL
            encoded_path = urllib.parse.quote(file_path)
            # Плеер будет открывать ссылку на наш сервер
            stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}"
            
            print(f"🚀 Запуск потока: {stream_url}")
            # Используем subprocess как советовала другая нейронка
            subprocess.Popen(['termux-open', stream_url])
        return True
    except Exception as e:
        print(f"⚠️ Ошибка запуска: {e}")
        return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Windows', '$Recycle.Bin', 'Program Files', 'AppData'}
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        video_library.append({"name": file.lower(), "path": os.path.join(root, file)})
    return video_library

@app.get("/")
async def root():
    return {"status": "Aura Online"}

@app.get("/video-stream")
async def video_stream(path: str):
    # СОВЕТ ДРУГОЙ НЕЙРОНКИ: Раскодируем путь обратно для системы
    decoded_path = urllib.parse.unquote(path)
    if os.path.exists(decoded_path):
        return FileResponse(decoded_path)
    print(f"❌ Файл не найден: {decoded_path}")
    return {"error": "File not found"}

@app.get("/search-movie")
async def search_movie(query: str):
    print(f"🔎 Запрос: {query}")
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
                score = fuzz.partial_ratio(var, video["name"])
                if score > highest_score:
                    highest_score = score
                    best_match = video

        if best_match and highest_score > 60:
            success = open_file(best_match['path'])
            return {"found": success, "filename": os.path.basename(best_match['path'])}
        return {"found": False}
    except Exception as e:
        print(f"☢️ Ошибка: {e}")
        return {"found": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)