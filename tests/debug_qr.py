#!/usr/bin/env python3
"""
Отладочный скрипт для QR-регистрации
"""
from utils.qr_registration import QRRegistrationManager
from models.meetup import MeetupManager
import sys
import os

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def debug_qr():
    """Отлаживает QR-регистрацию"""
    print("🔍 Отладка QR-регистрации...")

    # Инициализируем менеджеры
    qr_manager = QRRegistrationManager()
    meetup_manager = MeetupManager()

    print("✅ Менеджеры инициализированы")

    # Проверяем все митапы
    print(f"\n📊 Все митапы в meetup_manager:")
    for meetup_id, meetup in meetup_manager.meetups.items():
        print(f"  - {meetup['name']}: {meetup['status']} (ID: {meetup_id})")

    # Проверяем активные митапы через meetup_manager
    print(f"\n🎯 Активные митапы через meetup_manager:")
    active_meetups = meetup_manager.get_active_meetups()
    print(f"  Количество: {len(active_meetups)}")
    for meetup in active_meetups:
        print(f"  - {meetup['name']}: {meetup['status']}")

    # Проверяем активные митапы через qr_manager
    print(f"\n🔄 Активные митапы через qr_manager:")
    active_meetups_qr = qr_manager.get_active_meetups()
    print(f"  Количество: {len(active_meetups_qr)}")
    for meetup in active_meetups_qr:
        print(f"  - {meetup['name']}: {meetup['status']}")

    # Проверяем конкретный митап
    target_meetup_id = "f197b4a6-c383-4321-804c-6b14be1d539d"
    print(f"\n🎯 Проверка конкретного митапа {target_meetup_id}:")

    meetup = meetup_manager.get_meetup(target_meetup_id)
    if meetup:
        print(f"  Название: {meetup['name']}")
        print(f"  Статус: {meetup['status']}")
        print(f"  Дата: {meetup['date']}")
        print(f"  Время: {meetup['start_time']} - {meetup['end_time']}")

        # Проверяем, можно ли начать регистрацию
        can_start, message = qr_manager.can_start_registration(
            target_meetup_id)
        print(f"  Можно начать регистрацию: {can_start}")
        print(f"  Сообщение: {message}")
    else:
        print(f"  ❌ Митап не найден")

    print("\n✅ Отладка завершена")


if __name__ == "__main__":
    debug_qr()
