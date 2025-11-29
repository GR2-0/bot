#!/usr/bin/env python3
"""
Тест обработки часовых поясов для митапов
"""
from models.meetup import MeetupManager
import sys
import os
from datetime import datetime, timezone, timedelta

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_timezone():
    """Тестирует обработку часовых поясов"""
    print("🧪 Тестирование обработки часовых поясов...")

    # Инициализируем менеджер митапов
    meetup_manager = MeetupManager()

    # Получаем текущее время в московском часовом поясе
    moscow_now = meetup_manager.get_moscow_time()
    print(
        f"⏰ Текущее время (Москва): {moscow_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"   UTC: {moscow_now.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")

    # Тестируем парсинг времени
    test_date = "2024-01-15"
    test_time = "19:00"

    try:
        meetup_date = datetime.strptime(test_date, '%Y-%m-%d').date()
        start_time = datetime.strptime(test_time, '%H:%M').time()

        # Создаем datetime с московским часовым поясом
        meetup_start = datetime.combine(
            meetup_date, start_time, tzinfo=meetup_manager.moscow_tz)

        print(f"\n📅 Тестовая дата: {test_date}")
        print(f"🕐 Тестовое время: {test_time}")
        print(
            f"🔄 Созданный datetime (Москва): {meetup_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(
            f"   UTC: {meetup_start.utctime().strftime('%Y-%m-%d %H:%M:%S')}")

        # Проверяем, активен ли митап
        is_active = meetup_start <= moscow_now
        print(
            f"✅ Митап должен быть {'активным' if is_active else 'планируемым'}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

    # Проверяем все митапы
    print(f"\n📊 Проверка всех митапов:")
    meetup_manager.load_meetups()

    for meetup_id, meetup in meetup_manager.meetups.items():
        print(f"\n🎯 {meetup.get('name', 'Без названия')}")
        print(f"   Статус: {meetup.get('status', 'Не указан')}")
        print(f"   Дата: {meetup.get('date', 'Не указана')}")
        print(
            f"   Время: {meetup.get('start_time', 'Не указано')} - {meetup.get('end_time', 'Не указано')}")

        try:
            if meetup.get('date') and meetup.get('start_time'):
                meetup_date = datetime.strptime(
                    meetup['date'], '%Y-%m-%d').date()
                start_time = datetime.strptime(
                    meetup['start_time'], '%H:%M').time()
                meetup_start = datetime.combine(
                    meetup_date, start_time, tzinfo=meetup_manager.moscow_tz)

                print(
                    f"   Время начала (Москва): {meetup_start.strftime('%Y-%m-%d %H:%M:%S')}")
                print(
                    f"   Статус должен быть: {'active' if meetup_start <= moscow_now else 'planned'}")
        except Exception as e:
            print(f"   Ошибка проверки времени: {e}")

    print("\n✅ Тестирование завершено")


if __name__ == "__main__":
    test_timezone()
