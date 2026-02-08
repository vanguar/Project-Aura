#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 15

# Переменные окружения
export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
export PATH=/data/data/com.termux/files/usr/bin:$PATH

# AURA AI
export GEMINI_API_KEY="AIzaSyBj9ypgLkONgOsACD8TEtfsQ2OLACSgFUs"
export AURA_BOT_TOKEN="8250645018:AAG0NTcU2XQPYdjmwYE3jBN3dxRfvD_I1vM"
export AURA_SON_CHAT_ID="-1003578591855"

cd /data/data/com.termux/files/home

# ЖЕСТКАЯ ОЧИСТКА: убиваем старые процессы и освобождаем порт 8000
pkill -f python
sleep 2

# Запуск геолокации в фоне
nohup python -u geo_tracker.py >> geo_log.txt 2>&1 &

# Запуск основного сервера
python -u main.py >> boot_log.txt 2>&1


