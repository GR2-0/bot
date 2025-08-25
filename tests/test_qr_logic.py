#!/usr/bin/env python3
"""
Тест логики QR-регистрации без telegram модуля
"""
from models.meetup import MeetupManager
from models.points import PointsManager
from models.user import UserManager
import sys
import os

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_qr_logic():
    """Тестирует логику QR-регистрации"""
    print("🧪 Тестирование логики QR-регистрации...")

    # Инициализируем менеджеры
    meetup_manager = MeetupManager()
    points_manager = PointsManager()
    user_manager = UserManager()

    print("✅ Менеджеры инициализированы")

    # Обновляем статусы митапов
    meetup_manager.update_meetup_statuses()
    print("✅ Статусы митапов обновлены")

    # Получаем активные митапы
    active_meetups = meetup_manager.get_active_meetups()
    print(f"📊 Активных митапов: {len(active_meetups)}")

    if active_meetups:
        for meetup in active_meetups:
            print(f"🎯 {meetup['name']}: {meetup['status']}")

            # Проверяем, можно ли начать регистрацию
            meetup_id = meetup['id']

            # Симулируем проверку из QR registration manager
            if meetup_id in {}:  # active_registrations пустой
                print(f"   ❌ QR-регистрация уже активна")
            else:
                print(f"   ✅ QR-регистрация может быть запущена")

                # Проверяем статус митапа
                if meetup.get('status') == 'active':
                    print(f"   ✅ Митап активен")
                else:
                    print(
                        f"   ❌ Митап не активен (статус: {meetup.get('status')})")
    else:
        print("❌ Нет активных митапов")

    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    test_qr_logic()
