#!/bin/bash

# Очистка старых процессов
pkill -f main.py
pkill -f geo_tracker.py

echo "--- Запуск Проекта Аура (Авто-рестарт включен) ---"

# Функция для запуска бэкенда с авто-перезапуском
run_main() {
    until python main.py; do
        echo "Main server 'main.py' упал. Перезапуск через 5 секунд..."
        sleep 5
    done
}

# Функция для запуска трекера с авто-перезапуском
run_tracker() {
    until python geo_tracker.py; do
        echo "Tracker 'geo_tracker.py' упал. Перезапуск через 5 секунд..."
        sleep 5
    done
}

# Запуск функций в фоновом режиме
run_main &
run_tracker &

echo "Система активна. Для работы в фоне не забудьте включить 'Acquire wakelock' в уведомлениях Termux."