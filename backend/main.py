from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Добавлено для стриминга
import os
import platform
import string 
import urllib.parse # Добавлено для обработки путей
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

# --- Определение корней поиска ---
def get_search_roots():
    roots = []
    if platform.system() == "Windows":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append(drive)
    else:
        # Для Android используем папку, в которую ты перенес медиа
        roots = ['/storage/emulated/0/Movies/Aura/']
    return roots

SEARCH_ROOTS = get_search_roots()

# --- Универсальное открытие файла с фиксом для Android ---
def open_file(file_path):
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        else:
            # ФИКС: Вместо прямого пути передаем плееру HTTP-ссылку на этот же сервер
            encoded_path = urllib.parse.quote(file_path)
            stream_url = f"http://127.0.0.1:8000/video-stream?path={encoded_path}"
            print(f"🚀 Запуск потока для плеера: {stream_url}")
            os.system(f"termux-open '{stream_url}'")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка запуска: {e}")
        return False

def get_all_videos():
    video_library = []
    exclude_dirs = {'Windows', '$Recycle.Bin', 'Program Files', 'Program Files (x86)', 'AppData'}
    
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            print(f"🔎 Сканирую диск/путь: {root_dir}")
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        video_library.append({
                            "name": file.lower(),
                            "path": os.path.join(root, file)
                        })
    return video_library

@app.get("/")
async def root():
    return {"status": "Aura Universal Backend Online"}

# НОВЫЙ ЭНДПОИНТ: Отдает файл как поток (стриминг) для обхода защит Android
@app.get("/video-stream")
async def video_stream(path: str):
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "File not found"}

@app.get("/search-movie")
async def search_movie(query: str):
    print(f"🔎 Голосовой запрос: {query}")
    try:
        if not query:
            return {"found": False, "error": "Пустой запрос"}

        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        variants = [clean_query]
        try:
            variants.append(translit(clean_query, 'ru', reversed=True))
        except:
            pass

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
            print(f"✅ Найдено: {best_match['path']} ({highest_score}%)")
            success = open_file(best_match['path'])
            return {
                "found": success, 
                "filename": os.path.basename(best_match['path']),
                "score": highest_score
            }
        
        return {"found": False, "score": highest_score}

    except Exception as e:
        print(f"☢️ Ошибка: {e}")
        return {"found": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print(f"📀 Обнаружены диски для поиска: {SEARCH_ROOTS}")
    uvicorn.run(app, host="0.0.0.0", port=8000)