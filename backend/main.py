from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from thefuzz import fuzz
from transliterate import translit

app = FastAPI()

# Настройка CORS для связи фронтенда и бэкенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Список расширений видео, которые мы ищем автоматически
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.m4v'}

# Стандартные пути Android для поиска медиа
# /storage/emulated/0/ — это корень внутренней памяти
SEARCH_ROOTS = [
    '/storage/emulated/0/Movies',
    '/storage/emulated/0/Download',
    '/storage/emulated/0/DCIM',
    '/storage/emulated/0/Viber'
]

def open_on_android(file_path):
    """Открывает файл через системный плеер Android (через Termux)"""
    try:
        # Команда termux-open передает файл системному приложению (например, VLC для Android)
        os.system(f"termux-open '{file_path}'")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка запуска: {e}")
        return False

def get_all_videos():
    """Автоматически находит все видео во всех папках из SEARCH_ROOTS"""
    video_library = []
    for root_dir in SEARCH_ROOTS:
        if os.path.exists(root_dir):
            for root, dirs, files in os.walk(root_dir):
                for file in files:
                    # Проверяем расширение файла
                    if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        video_library.append({
                            "name": file.lower(),
                            "path": os.path.join(root, file)
                        })
    return video_library

@app.get("/")
async def root():
    return {"status": "Aura Android Backend Online"}

@app.get("/search-movie")
async def search_movie(query: str):
    print(f"🔎 Голосовой запрос: {query}")
    try:
        if not query:
            return {"found": False, "error": "Пустой запрос"}

        # Очистка и подготовка вариантов поиска
        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        variants = [clean_query]
        try:
            variants.append(translit(clean_query, 'ru', reversed=True))
        except:
            pass

        # Получаем актуальный список всех файлов на телефоне
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
            print(f"✅ Найдено автоматически: {best_match['path']} ({highest_score}%)")
            success = open_on_android(best_match['path'])
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