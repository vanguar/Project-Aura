#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
sleep 30
export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
export PATH=/data/data/com.termux/files/usr/bin:$PATH
cd /data/data/com.termux/files/home/backend

# Запуск геолокации в фоне
nohup python geo_tracker.py >> geo_log.txt 2>&1 &

# Запуск основного сервера
python -u main.py >> boot_log.txt 2>&1