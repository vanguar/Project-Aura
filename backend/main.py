from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
from thefuzz import fuzz
from transliterate import translit

app = FastAPI()

# Настройка CORS, чтобы смартфон и ноут могли общаться с бэкендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Список плееров для автозапуска (Windows)
KNOWN_PLAYERS = [
    {"name": "VLC", "path": r"C:\Program Files\VideoLAN\VLC\vlc.exe", "args": ["--fullscreen"]},
    {"name": "MPC-HC", "path": r"C:\Program Files\MPC-HC\mpc-hc64.exe", "args": ["/fullscreen"]}
]

def open_file(file_path):
    """Пытается открыть файл через известный плеер или средствами системы"""
    opened = False
    for player in KNOWN_PLAYERS:
        if os.path.exists(player["path"]):
            try:
                subprocess.Popen([player["path"]] + player["args"] + [file_path])
                opened = True
                break
            except:
                continue
    if not opened:
        os.startfile(file_path)

# Главная страница, чтобы не было 404 ошибки
@app.get("/")
async def root():
    return {
        "status": "online",
        "project": "Aura Assistive System",
        "endpoints": {
            "search": "/search-movie?query=название"
        }
    }

@app.get("/search-movie")
async def search_movie(query: str):
    print(f"🔎 Поступил запрос на поиск: {query}")
    try:
        if not query:
            return {"found": False, "error": "Пустой запрос"}

        # Очистка запроса от лишних слов
        clean_query = query.lower().replace("запусти", "").replace("фильм", "").strip()
        
        # Создаем варианты (оригинал и транслит)
        variants = [clean_query]
        try:
            # Превращаем "матрица" в "matritsa" для поиска по англ. именам файлов
            variants.append(translit(clean_query, 'ru', reversed=True))
        except Exception as e:
            print(f"⚠️ Ошибка транслитерации: {e}")

        best_match_path = None
        best_match_name = None
        highest_score = 0
        
        # ПАПКИ ДЛЯ ПОИСКА (проверь, что они есть на диске C)
        ROOT_FOLDERS = [r"C:\Movies", r"C:\Users\tzvan\Videos"] 

        for root_dir in ROOT_FOLDERS:
            if os.path.exists(root_dir):
                for root, dirs, files in os.walk(root_dir):
                    for file in files:
                        file_lower = file.lower()
                        for var in variants:
                            score = fuzz.partial_ratio(var, file_lower)
                            if score > highest_score:
                                highest_score = score
                                best_match_path = os.path.join(root, file)
                                best_match_name = file

        if best_match_path and highest_score > 60:
            print(f"✅ Найдено: {best_match_name} (Сходство: {highest_score}%)")
            open_file(best_match_path)
            return {
                "found": True, 
                "filename": best_match_name,
                "path": best_match_path,
                "score": highest_score
            }
        
        print(f"❌ Ничего не найдено для '{query}'")
        return {"found": False, "score": highest_score}

    except Exception as e:
        print(f"☢️ Критическая ошибка бэкенда: {e}")
        return {"found": False, "error": str(e)}

# Запуск сервера
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🚀 АУРА: Бэкенд запущен и готов к работе.")
    print("📍 Доступ на ноуте: http://localhost:8000")
    print("📍 Доступ в сети: http://0.0.0.0:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)