#!/usr/bin/env python3
"""
Тестовый скрипт для проверки очистки QR-сообщений
"""
from utils.qr_registration import QRRegistrationManager
import asyncio
import sys
import os

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


async def test_qr_cleanup():
    """Тестирует функциональность очистки QR-сообщений"""
    print("🧪 Тестирование очистки QR-сообщений...")

    # Инициализируем менеджер
    qr_manager = QRRegistrationManager()

    print("✅ Менеджер инициализирован")

    # Проверяем активные митапы
    active_meetups = qr_manager.get_active_meetups()
    print(f"📊 Активных митапов: {len(active_meetups)}")

    if active_meetups:
        print("🎯 Список активных митапов:")
        for meetup in active_meetups:
            print(
                f"  - {meetup['name']} ({meetup['date']}) - "
                f"{meetup['status']}"
            )

    # Проверяем активные регистрации
    active_registrations = qr_manager.get_all_active_registrations()
    print(f"🔄 Активных QR-регистраций: {len(active_registrations)}")

    if active_registrations:
        print("📱 Список активных регистраций:")
        for reg in active_registrations:
            print(
                f"  - {reg['meetup_name']} - "
                f"{reg['total_registrations']} участников"
            )

        # Тестируем очистку для первого активного митапа
        first_reg = active_registrations[0]
        meetup_id = first_reg['meetup_id']

        print(
            f"\n🧹 Тестируем очистку для митапа: "
            f"{first_reg['meetup_name']}"
        )

        try:
            success, message = await qr_manager.cleanup_old_qr_messages(
                meetup_id
            )
            print(f"Результат очистки: {success} - {message}")
        except Exception as e:
            print(f"Ошибка при очистке: {e}")

    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    asyncio.run(test_qr_cleanup())
