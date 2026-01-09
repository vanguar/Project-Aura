#!/bin/bash

# 1. Переход в папку по абсолютному пути (обсудили для корректной работы автозапуска)
cd /data/data/com.termux/files/home/aura

# 2. Очистка старых процессов
pkill -f main.py
pkill -f geo_tracker.py

echo "--- Запуск Проекта Аура (Авто-рестарт + Логирование) ---"

# 3. Функция для запуска бэкенда с записью логов (обсудили для поиска 'Ошибки сервера')
run_main() {
    until python main.py >> main.log 2>&1; do
        echo "$(date): Main server упал. Рестарт через 5 сек..." >> main.log
        sleep 5
    done
}

# 4. Функция для запуска трекера с записью логов
run_tracker() {
    until python geo_tracker.py >> tracker.log 2>&1; do
        echo "$(date): Tracker упал. Рестарт через 5 сек..." >> tracker.log
        sleep 5
    done
}

# Запуск в фоновом режиме
run_main &
run_tracker &

echo "Система запущена. Проверяй main.log в случае ошибки сервера."