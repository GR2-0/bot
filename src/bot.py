"""
Основной модуль бота GR2-0 Community Bot
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

from config import config
from messages import message_manager
from models.user import UserManager
from models.meetup import MeetupManager
from models.points import PointsManager
from utils.qr_generator import QRCodeGenerator
from utils.group_checker import GroupChecker
from utils.qr_registration import QRRegistrationManager
from polls import BotPollsHandlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для состояний
MOSCOW_TZ = timezone(timedelta(hours=3))

# Состояния для создания митапа
MEETUP_CREATION_TITLE = 1
MEETUP_CREATION_PRESENTATIONS = range(2, 9)
POLL_RESPONSE = range(9, 10)


class GR2Bot:
    """Основной класс бота GR2-0 Community"""

    def __init__(self):
        self.application = None
        self.user_manager = UserManager()
        self.meetup_manager = MeetupManager()
        self.points_manager = PointsManager()
        self.qr_generator = QRCodeGenerator()
        self.group_checker = GroupChecker()
        # Используем тот же экземпляр meetup_manager
        self.qr_registration = QRRegistrationManager()
        # Передаём существующий meetup_manager в QR registration manager
        self.qr_registration.meetup_manager = self.meetup_manager
        # Передаём существующий points_manager в QR registration manager
        self.qr_registration.points_manager = self.points_manager
        # Инициализируем обработчики опросов
        self.polls_handlers = None

    def get_moscow_time(self) -> datetime:
        """Возвращает текущее время в московском часовом поясе"""
        return datetime.now(MOSCOW_TZ)

    def get_moscow_date(self) -> str:
        """Возвращает текущую дату в московском часовом поясе в формате YYYY-MM-DD"""
        return self.get_moscow_time().strftime('%Y-%m-%d')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username

        logger.info(f"User {user_id} ({username}) started the bot")

        # Проверяем, зарегистрирован ли пользователь
        if not self.user_manager.is_user_registered(user_id):
            # Регистрация отключена
            await update.message.reply_text(
                "Не спеши, я напишу тебе про новые фишки ГР2.0👌"
            )
            return

        # Пользователь уже зарегистрирован
        await update.message.reply_text(
            "Привет! Я бот сообщества GR2.0. Используй /help для просмотра доступных команд."
        )

    async def handle_qr_registration_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, start_param: str):
        """Обрабатывает QR-регистрацию через команду /start"""
        user_id = str(update.effective_user.id)

        print(f"DEBUG: Handling QR registration start: {start_param}")

        # Парсим параметр start
        # Формат: register_meetup_id_hash
        try:
            parts = start_param.split('_')
            if len(parts) != 3:
                await update.message.reply_text("❌ Неверный формат QR-кода")
                return

            if parts[0] != "register":
                await update.message.reply_text("❌ Неверный формат QR-кода")
                return

            meetup_id = parts[1]
            hash_value = parts[2]

            # Проверяем хеш
            if not self.qr_registration.verify_registration_hash(meetup_id, hash_value):
                await update.message.reply_text("❌ QR-код недействителен или истек")
                return

            # Регистрируем пользователя на митап
            result = await self.qr_registration.register_user_for_meetup(
                user_id, meetup_id, update.effective_user.username
            )

            if result["success"]:
                await update.message.reply_text(
                    f"✅ Регистрация успешна!\n\n"
                    f"📅 Митап: {result['meetup_title']}\n"
                    f"📅 Дата: {result['meetup_date']}\n"
                    f"📍 Место: {result['meetup_location']}\n"
                    f"⏰ Время: {result['meetup_time']}\n\n"
                    f"🎉 Добро пожаловать на митап!"
                )
            else:
                await update.message.reply_text(f"❌ {result['message']}")

        except Exception as e:
            logger.error(f"Ошибка обработки QR-регистрации: {e}")
            await update.message.reply_text("❌ Ошибка обработки регистрации")

    async def meetup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /meetup (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                "➕ Создать митап", callback_data="meetup_add")],
            [InlineKeyboardButton("✏️ Редактировать митап",
                                  callback_data="meetup_edit")],
            [InlineKeyboardButton("🗑️ Удалить митап",
                                  callback_data="meetup_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📅 Управление митапами\n\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /admin (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                "📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(
                "👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("📅 Митапы", callback_data="admin_meetups")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔧 Админ-панель\n\nВыберите раздел:",
            reply_markup=reply_markup
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            # Получаем статистику
            total_users = self.user_manager.get_total_users()
            total_meetups = self.meetup_manager.get_total_meetups()
            total_points = self.points_manager.get_total_points()

            stats_text = (
                f"📊 Статистика бота\n\n"
                f"👥 Всего пользователей: {total_users}\n"
                f"📅 Всего митапов: {total_meetups}\n"
                f"⭐ Всего очков: {total_points}\n"
                f"🕐 Время: {self.get_moscow_time().strftime('%H:%M:%S')}"
            )

            await update.message.reply_text(stats_text)
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /users (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            users = self.user_manager.get_all_users()
            users_text = "👥 Список пользователей:\n\n"

            for user in users[:10]:  # Показываем только первых 10
                users_text += f"• {user.get('username', 'N/A')} (ID: {user.get('user_id', 'N/A')})\n"

            if len(users) > 10:
                users_text += f"\n... и еще {len(users) - 10} пользователей"

            await update.message.reply_text(users_text)
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей: {e}")
            await update.message.reply_text("❌ Ошибка получения списка пользователей")

    async def update_meetups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /update_meetups (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            await self.meetup_manager.update_meetups_from_api()
            await update.message.reply_text("✅ Митапы обновлены")
        except Exception as e:
            logger.error(f"Ошибка обновления митапов: {e}")
            await update.message.reply_text("❌ Ошибка обновления митапов")

    async def qr_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /qr_start (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            result = await self.qr_registration.start_registration()
            if result["success"]:
                await update.message.reply_text(
                    f"✅ QR-регистрация запущена!\n\n"
                    f"📅 Митап: {result['meetup_title']}\n"
                    f"🔗 Ссылка: {result['registration_url']}\n"
                    f"⏰ Действует до: {result['expires_at']}"
                )
            else:
                await update.message.reply_text(f"❌ {result['message']}")
        except Exception as e:
            logger.error(f"Ошибка запуска QR-регистрации: {e}")
            await update.message.reply_text("❌ Ошибка запуска QR-регистрации")

    async def qr_stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /qr_stop (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            result = await self.qr_registration.stop_registration()
            if result["success"]:
                await update.message.reply_text(
                    f"✅ QR-регистрация остановлена!\n\n"
                    f"📊 Зарегистрировано: {result['registered_count']} пользователей"
                )
            else:
                await update.message.reply_text(f"❌ {result['message']}")
        except Exception as e:
            logger.error(f"Ошибка остановки QR-регистрации: {e}")
            await update.message.reply_text("❌ Ошибка остановки QR-регистрации")

    async def qr_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /qr_status (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            status = await self.qr_registration.get_status()
            if status["active"]:
                await update.message.reply_text(
                    f"🟢 QR-регистрация активна\n\n"
                    f"📅 Митап: {status['meetup_title']}\n"
                    f"🔗 Ссылка: {status['registration_url']}\n"
                    f"⏰ Действует до: {status['expires_at']}\n"
                    f"📊 Зарегистрировано: {status['registered_count']} пользователей"
                )
            else:
                await update.message.reply_text("🔴 QR-регистрация неактивна")
        except Exception as e:
            logger.error(f"Ошибка получения статуса QR-регистрации: {e}")
            await update.message.reply_text("❌ Ошибка получения статуса")

    async def qr_cleanup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /qr_cleanup (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        try:
            result = await self.qr_registration.cleanup_expired_registrations()
            await update.message.reply_text(
                f"✅ Очистка завершена!\n\n"
                f"🗑️ Удалено: {result['cleaned_count']} истекших регистраций"
            )
        except Exception as e:
            logger.error(f"Ошибка очистки QR-регистраций: {e}")
            await update.message.reply_text("❌ Ошибка очистки")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()

        logger.info(f"Button callback received: {query.data}")

        # Обработка callback'ов опросов
        if (query.data.startswith("poll_") or query.data == "polls_active" or
                query.data == "polls_back"):
            await self.polls_handlers.handle_poll_callback(update, context)
            return

        if query.data == "meetup_add":
            await self.start_meetup_creation(query, context)
        elif query.data == "meetup_edit":
            await self.show_meetups_for_edit(query, context)
        elif query.data == "meetup_delete":
            await self.show_meetups_for_delete(query, context)
        elif query.data.startswith("edit_meetup_"):
            meetup_id = query.data.replace("edit_meetup_", "")
            await self.start_meetup_editing(query, context, meetup_id)
        elif query.data.startswith("delete_meetup_"):
            meetup_id = query.data.replace("delete_meetup_", "")
            await self.confirm_meetup_deletion(query, context, meetup_id)
        elif query.data.startswith("confirm_delete_"):
            meetup_id = query.data.replace("confirm_delete_", "")
            await self.delete_meetup(query, context, meetup_id)
        elif query.data == "admin_stats":
            await self.show_admin_stats(query, context)
        elif query.data == "admin_users":
            await self.show_admin_users(query, context)
        elif query.data == "admin_meetups":
            await self.show_admin_meetups(query, context)
        elif query.data == "back_to_admin":
            await self.show_admin_menu(query, context)
        elif query.data == "back_to_meetups":
            await self.show_meetup_menu(query, context)
        else:
            await query.edit_message_text("❌ Неизвестная команда")

    # Meetup management methods (simplified)
    async def start_meetup_creation(self, query, context):
        """Начинает создание митапа"""
        context.user_data['meetup_creation'] = {}
        context.user_data['meetup_creation']['step'] = 'title'

        await query.edit_message_text(
            "📅 Создание митапа\n\nВведите название митапа:"
        )

    async def show_meetups_for_edit(self, query, context):
        """Показывает список митапов для редактирования"""
        try:
            meetups = self.meetup_manager.get_all_meetups()
            if not meetups:
                await query.edit_message_text("📅 Митапы не найдены")
                return

            keyboard = []
            for meetup in meetups[:10]:  # Показываем только первые 10
                keyboard.append([InlineKeyboardButton(
                    f"✏️ {meetup['title']}",
                    callback_data=f"edit_meetup_{meetup['id']}"
                )])

            keyboard.append([InlineKeyboardButton(
                "⬅️ Назад", callback_data="back_to_meetups")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "✏️ Редактирование митапа\n\nВыберите митап:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка получения митапов: {e}")
            await query.edit_message_text("❌ Ошибка получения митапов")

    async def show_meetups_for_delete(self, query, context):
        """Показывает список митапов для удаления"""
        try:
            meetups = self.meetup_manager.get_all_meetups()
            if not meetups:
                await query.edit_message_text("📅 Митапы не найдены")
                return

            keyboard = []
            for meetup in meetups[:10]:  # Показываем только первые 10
                keyboard.append([InlineKeyboardButton(
                    f"🗑️ {meetup['title']}",
                    callback_data=f"delete_meetup_{meetup['id']}"
                )])

            keyboard.append([InlineKeyboardButton(
                "⬅️ Назад", callback_data="back_to_meetups")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🗑️ Удаление митапа\n\nВыберите митап:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка получения митапов: {e}")
            await query.edit_message_text("❌ Ошибка получения митапов")

    async def start_meetup_editing(self, query, context, meetup_id):
        """Начинает редактирование митапа"""
        try:
            meetup = self.meetup_manager.get_meetup_by_id(meetup_id)
            if not meetup:
                await query.edit_message_text("❌ Митап не найден")
                return

            context.user_data['meetup_editing'] = {
                'meetup_id': meetup_id,
                'step': 'title'
            }

            await query.edit_message_text(
                f"✏️ Редактирование митапа\n\n"
                f"Текущее название: {meetup['title']}\n\n"
                f"Введите новое название:"
            )
        except Exception as e:
            logger.error(f"Ошибка начала редактирования: {e}")
            await query.edit_message_text("❌ Ошибка начала редактирования")

    async def confirm_meetup_deletion(self, query, context, meetup_id):
        """Подтверждает удаление митапа"""
        try:
            meetup = self.meetup_manager.get_meetup_by_id(meetup_id)
            if not meetup:
                await query.edit_message_text("❌ Митап не найден")
                return

            keyboard = [
                [InlineKeyboardButton(
                    "✅ Да, удалить", callback_data=f"confirm_delete_{meetup_id}")],
                [InlineKeyboardButton(
                    "❌ Отмена", callback_data="back_to_meetups")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🗑️ Подтверждение удаления\n\n"
                f"Вы уверены, что хотите удалить митап:\n"
                f"📅 {meetup['title']}\n\n"
                f"⚠️ Это действие нельзя отменить!",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка подтверждения удаления: {e}")
            await query.edit_message_text("❌ Ошибка подтверждения удаления")

    async def delete_meetup(self, query, context, meetup_id):
        """Удаляет митап"""
        try:
            result = self.meetup_manager.delete_meetup(meetup_id)
            if result:
                await query.edit_message_text("✅ Митап удален")
            else:
                await query.edit_message_text("❌ Ошибка удаления митапа")
        except Exception as e:
            logger.error(f"Ошибка удаления митапа: {e}")
            await query.edit_message_text("❌ Ошибка удаления митапа")

    async def show_admin_stats(self, query, context):
        """Показывает статистику в админ-панели"""
        try:
            total_users = self.user_manager.get_total_users()
            total_meetups = self.meetup_manager.get_total_meetups()
            total_points = self.points_manager.get_total_points()

            stats_text = (
                f"📊 Статистика\n\n"
                f"👥 Пользователей: {total_users}\n"
                f"📅 Митапов: {total_meetups}\n"
                f"⭐ Очков: {total_points}\n"
                f"🕐 Время: {self.get_moscow_time().strftime('%H:%M:%S')}"
            )

            keyboard = [[InlineKeyboardButton(
                "⬅️ Назад", callback_data="back_to_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(stats_text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await query.edit_message_text("❌ Ошибка получения статистики")

    async def show_admin_users(self, query, context):
        """Показывает пользователей в админ-панели"""
        try:
            users = self.user_manager.get_all_users()
            users_text = "👥 Пользователи:\n\n"

            for user in users[:10]:  # Показываем только первых 10
                users_text += f"• {user.get('username', 'N/A')} (ID: {user.get('user_id', 'N/A')})\n"

            if len(users) > 10:
                users_text += f"\n... и еще {len(users) - 10} пользователей"

            keyboard = [[InlineKeyboardButton(
                "⬅️ Назад", callback_data="back_to_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(users_text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            await query.edit_message_text("❌ Ошибка получения пользователей")

    async def show_admin_meetups(self, query, context):
        """Показывает митапы в админ-панели"""
        try:
            meetups = self.meetup_manager.get_all_meetups()
            meetups_text = "📅 Митапы:\n\n"

            for meetup in meetups[:10]:  # Показываем только первые 10
                meetups_text += f"• {meetup['title']} ({meetup['date']})\n"

            if len(meetups) > 10:
                meetups_text += f"\n... и еще {len(meetups) - 10} митапов"

            keyboard = [[InlineKeyboardButton(
                "⬅️ Назад", callback_data="back_to_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(meetups_text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка получения митапов: {e}")
            await query.edit_message_text("❌ Ошибка получения митапов")

    async def show_admin_menu(self, query, context):
        """Показывает главное меню админ-панели"""
        keyboard = [
            [InlineKeyboardButton(
                "📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(
                "👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("📅 Митапы", callback_data="admin_meetups")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔧 Админ-панель\n\nВыберите раздел:",
            reply_markup=reply_markup
        )

    async def show_meetup_menu(self, query, context):
        """Показывает меню управления митапами"""
        keyboard = [
            [InlineKeyboardButton(
                "➕ Создать митап", callback_data="meetup_add")],
            [InlineKeyboardButton("✏️ Редактировать митап",
                                  callback_data="meetup_edit")],
            [InlineKeyboardButton("🗑️ Удалить митап",
                                  callback_data="meetup_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📅 Управление митапами\n\nВыберите действие:",
            reply_markup=reply_markup
        )

    async def handle_meetup_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовые сообщения для создания/редактирования митапов"""
        if 'meetup_creation' in context.user_data:
            await self.handle_meetup_creation_text(update, context)
        elif 'meetup_editing' in context.user_data:
            await self.handle_meetup_editing_text(update, context)

    async def handle_meetup_creation_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовые сообщения при создании митапа"""
        text = update.message.text
        step = context.user_data['meetup_creation']['step']

        if step == 'title':
            context.user_data['meetup_creation']['title'] = text
            context.user_data['meetup_creation']['step'] = 'complete'

            # Создаем митап
            try:
                meetup_data = {
                    'title': text,
                    'date': self.get_moscow_date(),
                    'location': 'TBD',
                    'description': 'Создан через бота'
                }

                meetup_id = self.meetup_manager.create_meetup(meetup_data)

                await update.message.reply_text(
                    f"✅ Митап создан!\n\n"
                    f"📅 Название: {text}\n"
                    f"🆔 ID: {meetup_id}\n"
                    f"📅 Дата: {self.get_moscow_date()}"
                )

                # Очищаем данные
                del context.user_data['meetup_creation']

            except Exception as e:
                logger.error(f"Ошибка создания митапа: {e}")
                await update.message.reply_text("❌ Ошибка создания митапа")

    async def handle_meetup_editing_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовые сообщения при редактировании митапа"""
        text = update.message.text
        step = context.user_data['meetup_editing']['step']
        meetup_id = context.user_data['meetup_editing']['meetup_id']

        if step == 'title':
            try:
                # Обновляем название митапа
                result = self.meetup_manager.update_meetup(
                    meetup_id, {'title': text})

                if result:
                    await update.message.reply_text(
                        f"✅ Название митапа обновлено!\n\n"
                        f"📅 Новое название: {text}"
                    )
                else:
                    await update.message.reply_text("❌ Ошибка обновления митапа")

                # Очищаем данные
                del context.user_data['meetup_editing']

            except Exception as e:
                logger.error(f"Ошибка обновления митапа: {e}")
                await update.message.reply_text("❌ Ошибка обновления митапа")

    async def _cleanup_task(self):
        """Задача очистки истекших регистраций"""
        while True:
            try:
                await asyncio.sleep(300)  # Проверяем каждые 5 минут
                await self.qr_registration.cleanup_expired_registrations()
            except Exception as e:
                logger.error(f"Ошибка в задаче очистки: {e}")
                await asyncio.sleep(60)  # Ждём минуту при ошибке

    def setup_handlers(self):
        """Настраивает обработчики команд и сообщений"""
        # Инициализируем обработчики опросов
        self.polls_handlers = BotPollsHandlers(
            self.user_manager, self.application)

        # Админские команды
        self.application.add_handler(
            CommandHandler("meetup", self.meetup_command))
        self.application.add_handler(
            CommandHandler("admin", self.admin_command))
        self.application.add_handler(
            CommandHandler("stats", self.stats_command))
        self.application.add_handler(
            CommandHandler("users", self.users_command))
        self.application.add_handler(
            CommandHandler("update_meetups", self.update_meetups_command))
        self.application.add_handler(
            CommandHandler("qr_start", self.qr_start_command))
        self.application.add_handler(
            CommandHandler("qr_stop", self.qr_stop_command))
        self.application.add_handler(
            CommandHandler("qr_status", self.qr_status_command))
        self.application.add_handler(
            CommandHandler("qr_cleanup", self.qr_cleanup_command))
        self.application.add_handler(
            CommandHandler("polls", self.polls_handlers.polls_command))

        # Обработчики кнопок
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback))

        # Простой обработчик команды /start для QR-кодов (без регистрации)
        self.application.add_handler(CommandHandler("start", self.start))

        # Обработчик для ответов на опросы (должен быть первым)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND,
                           self.polls_handlers.handle_poll_text_response)
        )

        # Обработчик для создания и редактирования митапов (перехватывает все текстовые сообщения)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND,
                           self.handle_meetup_text)
        )

    async def run(self):
        """Запускает бота"""
        try:
            # Очищаем переменные окружения для прокси
            import os
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''
            os.environ['ALL_PROXY'] = ''
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''
            os.environ['all_proxy'] = ''

            # Создаём приложение
            self.application = Application.builder().token(
                config.get_bot_token()).build()

            # Инициализируем GroupChecker с токеном бота
            await self.group_checker.initialize_bot(config.get_bot_token())

            # Настраиваем обработчики
            self.setup_handlers()

            # Запускаем бота
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            # Запускаем задачу очистки истекших регистраций
            asyncio.create_task(self._cleanup_task())

            logger.info("Бот запущен успешно!")

            # Держим бота запущенным - в v20 используем asyncio.Event
            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")
            finally:
                await self.application.stop()
                await self.application.shutdown()

        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise


if __name__ == "__main__":
    bot = GR2Bot()
    asyncio.run(bot.run())
