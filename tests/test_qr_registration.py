#!/usr/bin/env python3
"""
Тестовый скрипт для проверки QR-регистрации
"""
from utils.qr_registration import QRRegistrationManager
from models.meetup import MeetupManager
from models.points import PointsManager
from models.user import UserManager
import asyncio
import sys
import os

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


async def test_qr_registration():
    """Тестирует функциональность QR-регистрации"""
    print("🧪 Тестирование QR-регистрации...")

    # Инициализируем менеджеры
    qr_manager = QRRegistrationManager()
    meetup_manager = MeetupManager()
    points_manager = PointsManager()
    user_manager = UserManager()

    print("✅ Менеджеры инициализированы")

    # Проверяем активные митапы
    active_meetups = qr_manager.get_active_meetups()
    print(f"📊 Активных митапов: {len(active_meetups)}")

    if active_meetups:
        print("🎯 Список активных митапов:")
        for meetup in active_meetups:
            print(
                f"  - {meetup['name']} ({meetup['date']}) - {meetup['status']}")

    # Проверяем активные регистрации
    active_registrations = qr_manager.get_all_active_registrations()
    print(f"🔄 Активных QR-регистраций: {len(active_registrations)}")

    if active_registrations:
        print("📱 Список активных регистраций:")
        for reg in active_registrations:
            print(
                f"  - {reg['meetup_name']} - {reg['total_registrations']} участников")

    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    asyncio.run(test_qr_registration())
