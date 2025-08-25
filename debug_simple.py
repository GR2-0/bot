#!/usr/bin/env python3
"""
Простой отладочный скрипт для проверки митапов
"""
from models.meetup import MeetupManager
import sys
import os

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def debug_simple():
    """Простая отладка митапов"""
    print("🔍 Простая отладка митапов...")

    # Инициализируем менеджер митапов
    meetup_manager = MeetupManager()

    print("✅ Менеджер митапов инициализирован")

    # Проверяем все митапы
    print(f"\n📊 Все митапы:")
    for meetup_id, meetup in meetup_manager.meetups.items():
        print(f"  - {meetup['name']}: {meetup['status']} (ID: {meetup_id})")

    # Проверяем активные митапы
    print(f"\n🎯 Активные митапы:")
    active_meetups = meetup_manager.get_active_meetups()
    print(f"  Количество: {len(active_meetups)}")
    for meetup in active_meetups:
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

        # Проверяем статус
        if meetup['status'] == 'active':
            print(f"  ✅ Митап активен")
        else:
            print(f"  ❌ Митап не активен (статус: {meetup['status']})")
    else:
        print(f"  ❌ Митап не найден")

    print("\n✅ Отладка завершена")


if __name__ == "__main__":
    debug_simple()
