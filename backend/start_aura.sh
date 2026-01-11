#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 30

# Переменные окружения
export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
export PATH=/data/data/com.termux/files/usr/bin:$PATH
cd /data/data/com.termux/files/home/backend

# === НОВАЯ ЧАСТЬ: Очистка зависших процессов ===
# Убиваем старые копии, если они остались после сбоя или перезагрузки
pkill -f python
sleep 2

# Запуск геолокации в фоне
nohup python -u geo_tracker.py >> geo_log.txt 2>&1 &

# Запуск основного сервера
python -u main.py >> boot_log.txt 2>&1