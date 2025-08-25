"""
Модуль для управления QR-регистрацией на митапы
"""
import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from telegram import Bot

from models.meetup import MeetupManager
from models.user import UserManager
from utils.qr_generator import QRCodeGenerator
from config import config


class QRRegistrationManager:
    """Класс для управления QR-регистрацией на митапы"""

    def __init__(self):
        self.meetup_manager = MeetupManager()
        self.points_manager = None  # Будет установлен извне
        self.user_manager = UserManager()
        self.qr_generator = QRCodeGenerator()
        self.active_registrations = {}  # meetup_id -> registration_data
        self.registration_tasks = {}  # meetup_id -> asyncio.Task
        self.moscow_tz = timezone(timedelta(hours=3))

    def get_moscow_time(self) -> datetime:
        """Возвращает текущее время в московском часовом поясе"""
        return datetime.now(self.moscow_tz)

    def get_moscow_date(self) -> str:
        """Возвращает текущую дату в московском часовом поясе"""
        return self.get_moscow_time().strftime('%Y-%m-%d')

    def get_moscow_datetime(self) -> str:
        """Возвращает текущее время в московском часовом поясе в ISO формате"""
        return self.get_moscow_time().isoformat()

    def generate_registration_hash(self, meetup_id: str, user_id: str) -> str:
        """Генерирует хеш для регистрации на митап"""
        timestamp = str(int(self.get_moscow_time().timestamp()))
        data = f"{meetup_id}:{user_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def create_registration_deep_link(self, meetup_id: str, hash_code: str) -> str:
        """Создаёт диплинк для регистрации на митап"""
        # Получаем username бота из конфигурации
        bot_username = config.get_bot_username()
        base_url = f"https://t.me/{bot_username}"
        return f"{base_url}?start=register_{meetup_id}_{hash_code}"

    def get_active_meetups(self) -> List[Dict]:
        """Возвращает список активных митапов"""
        print(f"DEBUG: QRRegistrationManager.get_active_meetups() вызван")
        print(
            f"DEBUG: meetup_manager.meetups содержит {len(self.meetup_manager.meetups)} митапов")

        active_meetups = self.meetup_manager.get_active_meetups()
        print(
            f"DEBUG: meetup_manager.get_active_meetups() вернул {len(active_meetups)} митапов")

        return active_meetups

    def can_start_registration(self, meetup_id: str) -> Tuple[bool, str]:
        """Проверяет, можно ли начать QR-регистрацию для митапа"""
        if meetup_id in self.active_registrations:
            return False, ("QR-регистрация уже активна для этого митапа")

        meetup = self.meetup_manager.get_meetup(meetup_id)
        if not meetup:
            return False, "Митап не найден"

        if meetup.get('status') != 'active':
            return False, ("Митап должен быть активным для QR-регистрации")

        return True, "OK"

    def start_registration(self, meetup_id: str, admin_id: str) -> Tuple[bool, str]:
        """Начинает QR-регистрацию для митапа"""
        can_start, message = self.can_start_registration(meetup_id)
        if not can_start:
            return False, message

        meetup = self.meetup_manager.get_meetup(meetup_id)

        # Создаём данные регистрации
        registration_data = {
            'meetup_id': meetup_id,
            'meetup_name': meetup['name'],
            'admin_id': admin_id,
            'started_at': self.get_moscow_datetime(),
            'current_qr_hash': None,
            'qr_generation_active': True,
            'total_registrations': 0,
            'last_qr_sent_at': None
        }

        self.active_registrations[meetup_id] = registration_data

        # Запускаем задачу генерации QR-кодов
        task = asyncio.create_task(self._qr_generation_loop(meetup_id))
        self.registration_tasks[meetup_id] = task

        return True, (f"QR-регистрация запущена для митапа "
                      f"'{meetup['name']}'")

    def stop_registration(self, meetup_id: str) -> Tuple[bool, str]:
        """Останавливает QR-регистрацию для митапа"""
        if meetup_id not in self.active_registrations:
            return False, "QR-регистрация не активна для этого митапа"

        # Очищаем все файлы QR-кодов для этого митапа
        registration = self.active_registrations[meetup_id]
        if 'qr_messages' in registration:
            for msg_data in registration['qr_messages']:
                try:
                    if os.path.exists(msg_data['file_path']):
                        os.remove(msg_data['file_path'])
                        print(
                            f"Удалён файл QR-кода при остановке: {msg_data['file_path']}")
                except Exception as e:
                    print(f"Ошибка удаления файла QR-кода: {e}")

        # Останавливаем задачу генерации
        if meetup_id in self.registration_tasks:
            task = self.registration_tasks[meetup_id]
            if not task.done():
                task.cancel()
            del self.registration_tasks[meetup_id]

        # Очищаем данные регистрации
        meetup_name = self.active_registrations[meetup_id]['meetup_name']
        del self.active_registrations[meetup_id]

        return True, f"QR-регистрация остановлена для митапа '{meetup_name}'"

    async def _qr_generation_loop(self, meetup_id: str):
        """Основной цикл генерации QR-кодов"""
        try:
            while meetup_id in self.active_registrations:
                registration = self.active_registrations[meetup_id]

                if not registration['qr_generation_active']:
                    break

                # Проверяем, не завершился ли митап
                meetup = self.meetup_manager.get_meetup(meetup_id)
                if not meetup or meetup.get('status') != 'active':
                    await self._stop_registration_auto(meetup_id, "Митап завершён")
                    break

                # Генерируем новый QR-код
                await self._generate_new_qr(meetup_id)

                # Ждём указанный интервал
                interval = config.get_qr_interval()
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            # Задача была отменена
            pass
        except Exception as e:
            print(
                f"Ошибка в цикле генерации QR-кодов для митапа {meetup_id}: {e}")
            await self._stop_registration_auto(meetup_id, f"Ошибка: {str(e)}")

    async def _generate_new_qr(self, meetup_id: str):
        """Генерирует новый QR-код для митапа"""
        if meetup_id not in self.active_registrations:
            return

        registration = self.active_registrations[meetup_id]

        # Генерируем уникальный хеш для QR-кода
        timestamp = str(int(self.get_moscow_time().timestamp()))
        random_suffix = str(uuid.uuid4())[:8]
        qr_hash = hashlib.sha256(
            f"{meetup_id}:{timestamp}:{random_suffix}".encode()).hexdigest()[:16]

        # Обновляем данные регистрации
        registration['current_qr_hash'] = qr_hash
        registration['last_qr_sent_at'] = self.get_moscow_datetime()

        # Очищаем старые QR-сообщения и файлы
        await self._cleanup_old_qr_messages(meetup_id)

        # Отправляем QR-код админу
        await self._send_qr_to_admin(meetup_id, qr_hash)

    async def _send_qr_to_admin(self, meetup_id: str, qr_hash: str):
        """Отправляет QR-код админу"""
        if meetup_id not in self.active_registrations:
            return

        registration = self.active_registrations[meetup_id]
        admin_id = registration['admin_id']

        # Создаём диплинк
        deep_link = self.create_registration_deep_link(meetup_id, qr_hash)

        # Генерируем QR-код
        qr_file_path = self.qr_generator.generate_qr_code(meetup_id, deep_link)

        if qr_file_path:
            # Отправляем QR-код админу
            try:
                bot = Bot(token=config.get_bot_token())

                message_text = f"🔄 Новый QR-код для митапа '{registration['meetup_name']}'\n\n"
                message_text += f"📱 Хеш: `{qr_hash}`\n"
                message_text += f"🔗 Ссылка: {deep_link}\n\n"
                message_text += f"⏰ Сгенерирован: {registration['last_qr_sent_at']}\n"
                message_text += f"👥 Зарегистрировано: {registration['total_registrations']}"

                # Отправляем QR-код и сохраняем message_id для последующего удаления
                sent_message = await bot.send_photo(
                    chat_id=admin_id,
                    photo=open(qr_file_path, 'rb'),
                    caption=message_text,
                    parse_mode='Markdown'
                )

                # Сохраняем message_id для последующего удаления
                if 'qr_messages' not in registration:
                    registration['qr_messages'] = []
                registration['qr_messages'].append({
                    'message_id': sent_message.message_id,
                    'qr_hash': qr_hash,
                    'file_path': qr_file_path
                })

                await bot.close()

            except Exception as e:
                print(f"Ошибка отправки QR-кода админу: {e}")
                # Удаляем файл в случае ошибки
                if qr_file_path and os.path.exists(qr_file_path):
                    os.remove(qr_file_path)

    async def _cleanup_old_qr_messages(self, meetup_id: str):
        """Очищает старые QR-сообщения и файлы"""
        if meetup_id not in self.active_registrations:
            return

        registration = self.active_registrations[meetup_id]
        if 'qr_messages' not in registration:
            return

        current_time = self.get_moscow_time()
        current_hash = registration.get('current_qr_hash')

        # Очищаем старые сообщения (кроме текущего активного)
        messages_to_remove = []
        for msg_data in registration['qr_messages']:
            if msg_data['qr_hash'] != current_hash:
                messages_to_remove.append(msg_data)

        # Удаляем старые сообщения и файлы
        for msg_data in messages_to_remove:
            try:
                # Удаляем файл QR-кода
                if os.path.exists(msg_data['file_path']):
                    os.remove(msg_data['file_path'])
                    print(f"Удалён файл QR-кода: {msg_data['file_path']}")
            except Exception as e:
                print(f"Ошибка удаления файла QR-кода: {e}")

        # Удаляем старые записи из списка сообщений
        registration['qr_messages'] = [
            msg for msg in registration['qr_messages']
            if msg['qr_hash'] == current_hash
        ]

    async def _stop_registration_auto(self, meetup_id: str, reason: str):
        """Автоматически останавливает регистрацию"""
        if meetup_id in self.active_registrations:
            meetup_name = self.active_registrations[meetup_id]['meetup_name']
            print(
                f"Автоматическая остановка QR-регистрации для митапа '{meetup_name}': {reason}")

            # Очищаем все файлы QR-кодов для этого митапа
            registration = self.active_registrations[meetup_id]
            if 'qr_messages' in registration:
                for msg_data in registration['qr_messages']:
                    try:
                        if os.path.exists(msg_data['file_path']):
                            os.remove(msg_data['file_path'])
                            print(
                                f"Удалён файл QR-кода при автоматической остановке: {msg_data['file_path']}")
                    except Exception as e:
                        print(f"Ошибка удаления файла QR-кода: {e}")

            # Останавливаем задачу
            if meetup_id in self.registration_tasks:
                task = self.registration_tasks[meetup_id]
                if not task.done():
                    task.cancel()
                del self.registration_tasks[meetup_id]

            # Очищаем данные
            del self.active_registrations[meetup_id]

    def process_registration_request(self, meetup_id: str, hash_code: str, user_id: str) -> Tuple[bool, str]:
        """Обрабатывает запрос на регистрацию по QR-коду"""
        if meetup_id not in self.active_registrations:
            return False, "QR-регистрация не активна для этого митапа"

        registration = self.active_registrations[meetup_id]

        # Проверяем, совпадает ли хеш
        if registration['current_qr_hash'] != hash_code:
            return False, "Неверный QR-код"

        # Проверяем, не зарегистрирован ли уже пользователь
        meetup = self.meetup_manager.get_meetup(meetup_id)
        if not meetup:
            return False, "Митап не найден"

        attendees = meetup.get('attendees', [])
        if any(att['user_id'] == user_id for att in attendees):
            return False, "Вы уже зарегистрированы на этот митап"

        try:
            # Добавляем пользователя на митап
            self.meetup_manager.add_attendee(meetup_id, user_id)

            # Начисляем поинты за посещение митапа
            points = config.get_points_for_action("meetup_attendance")
            if points > 0:
                self.points_manager.add_points(
                    user_id, points, "meetup_attendance")

            # Обновляем статистику
            registration['total_registrations'] += 1

            return True, f"Успешная регистрация! Начислено {points} поинтов за посещение митапа."

        except Exception as e:
            return False, f"Ошибка регистрации: {str(e)}"

    def get_registration_status(self, meetup_id: str) -> Optional[Dict]:
        """Возвращает статус QR-регистрации для митапа"""
        if meetup_id not in self.active_registrations:
            return None

        return self.active_registrations[meetup_id].copy()

    def get_all_active_registrations(self) -> List[Dict]:
        """Возвращает все активные QR-регистрации"""
        return [
            {
                'meetup_id': meetup_id,
                'meetup_name': data['meetup_name'],
                'admin_id': data['admin_id'],
                'started_at': data['started_at'],
                'total_registrations': data['total_registrations'],
                'last_qr_sent_at': data['last_qr_sent_at']
            }
            for meetup_id, data in self.active_registrations.items()
        ]

    def cleanup_expired_registrations(self):
        """Очищает истекшие регистрации"""
        current_time = self.get_moscow_time()

        for meetup_id in list(self.active_registrations.keys()):
            meetup = self.meetup_manager.get_meetup(meetup_id)
            if not meetup or meetup.get('status') != 'active':
                # Автоматически останавливаем регистрацию
                asyncio.create_task(self._stop_registration_auto(
                    meetup_id, "Митап завершён"))

    def is_registration_active(self, meetup_id: str) -> bool:
        """Проверяет, активна ли QR-регистрация для митапа"""
        return meetup_id in self.active_registrations
