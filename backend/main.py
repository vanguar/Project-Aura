from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import platform
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

# --- ИЗМЕНЕНИЕ 1: Авто-определение папок поиска ---
if platform.system() == "Windows":
    # Пути для ноутбука (стандартные папки пользователя)
    user_path = os.path.expanduser("~")
    SEARCH_ROOTS = [
        os.path.join(user_path, "Videos"),
        os.path.join(user_path, "Downloads"),
        os.path.join(user_path, "Desktop")
    ]
else:
    # Твои стандартные пути для Android
    SEARCH_ROOTS = [
        '/storage/emulated/0/Movies',
        '/storage/emulated/0/Download',
        '/storage/emulated/0/DCIM',
        '/storage/emulated/0/Viber'
    ]

# --- ИЗМЕНЕНИЕ 2: Универсальное открытие файла ---
def open_file(file_path):
    try:
        if platform.system() == "Windows":
            os.startfile(file_path) # Для ноутбука
        else:
            os.system(f"termux-open '{file_path}'") # Твоя команда для Android
        return True
    except Exception as e:
        print(f"⚠️ Ошибка запуска: {e}")
        return False

def get_all_videos():
    video_library = []
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
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
            # --- ИЗМЕНЕНИЕ 3: Вызов универсальной функции ---
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
    uvicorn.run(app, host="0.0.0.0", port=8000)