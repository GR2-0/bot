"""
Основной модуль бота GR2-0 Community Bot
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from telegram.error import TelegramError

from config import config
from messages import message_manager
from models.user import UserManager
from models.meetup import MeetupManager
from models.points import PointsManager
from utils.qr_generator import QRCodeGenerator
from utils.group_checker import GroupChecker

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

# Состояния для ConversationHandler
REGISTRATION_NAME, REGISTRATION_INFO = range(2)
MEETUP_CREATION_NAME, MEETUP_CREATION_DATE, MEETUP_CREATION_TIME_START, \
    MEETUP_CREATION_TIME_END, MEETUP_CREATION_LOCATION, MEETUP_CREATION_CAPACITY, \
    MEETUP_CREATION_PRESENTATIONS = range(2, 9)


class GR2Bot:
    """Основной класс бота GR2-0 Community"""

    def __init__(self):
        self.application = None
        self.user_manager = UserManager()
        self.meetup_manager = MeetupManager()
        self.points_manager = PointsManager()
        self.qr_generator = QRCodeGenerator()
        self.group_checker = GroupChecker()

    def get_moscow_time(self) -> datetime:
        """Возвращает текущее время в московском часовом поясе"""
        return datetime.now(MOSCOW_TZ)

    def get_moscow_date(self) -> str:
        """Возвращает текущую дату в московском часовом поясе"""
        return self.get_moscow_time().strftime('%Y-%m-%d')

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name

        print(f"DEBUG: Start command from user {user_id} ({username})")

        # Проверяем, зарегистрирован ли пользователь
        if self.user_manager.user_exists(user_id):
            await update.message.reply_text(
                message_manager.get_welcome_message(is_new_user=False)
            )
            return

        # Проверяем, состоит ли пользователь в группе
        if not await self.group_checker.is_user_in_community(user_id):
            await update.message.reply_text(
                message_manager.get_registration_message("not_in_group")
            )
            return

        # Начинаем процесс регистрации
        context.user_data['registration_user_id'] = user_id
        context.user_data['registration_username'] = username

        await update.message.reply_text(
            message_manager.get_registration_message("ask_name")
        )

        return REGISTRATION_NAME

    async def registration_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода имени при регистрации"""
        user_id = context.user_data.get('registration_user_id')
        username = context.user_data.get('registration_username')
        name = update.message.text

        context.user_data['registration_name'] = name

        await update.message.reply_text(
            message_manager.get_registration_message("ask_info")
        )

        return REGISTRATION_INFO

    async def registration_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ввода информации при регистрации"""
        user_id = context.user_data.get('registration_user_id')
        username = context.user_data.get('registration_username')
        name = context.user_data.get('registration_name')
        info = update.message.text

        # Создаём пользователя
        user_data = {
            'id': user_id,
            'username': username,
            'name': name,
            'info': info,
            'registration_date': self.get_moscow_date(),
            'role': 'user'
        }

        self.user_manager.create_user(user_data)

        # Начисляем поинты за регистрацию
        points = config.get_points_for_action("registration")
        print(f"DEBUG: Registration points from config: {points}")
        print(f"DEBUG: Adding points to user {user_id}")
        self.points_manager.add_points(user_id, points, "registration")
        current_points = self.points_manager.get_user_points(user_id)
        print(f"DEBUG: Points added, checking current points: "
              f"{current_points}")

        await update.message.reply_text(
            message_manager.get_registration_message("success")
        )

        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        user_id = str(update.effective_user.id)
        is_admin = self.user_manager.is_admin(user_id)

        help_text = message_manager.get_help_message(is_admin=is_admin)
        await update.message.reply_text(help_text)

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.user_exists(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("user_not_found")
            )
            return

        user = self.user_manager.get_user(user_id)
        points = self.points_manager.get_user_points(user_id)

        print(f"DEBUG: Profile command for user {user_id}")
        print(f"DEBUG: User data: {user}")
        print(f"DEBUG: Points from PointsManager: {points}")

        profile_text = f"👤 Профиль\n\n"
        profile_text += f"Имя: {user.get('name', 'Не указано')}\n"
        profile_text += f"Роль: {user.get('role', 'user')}\n"
        profile_text += f"Дата регистрации: {user.get('registration_date', 'Не указано')}\n"
        profile_text += f"Поинты: {points} 💎\n"

        if user.get('info'):
            profile_text += f"О себе: {user['info']}\n"

        await update.message.reply_text(profile_text)

    async def points_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /points"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.user_exists(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("user_not_found")
            )
            return

        points = self.points_manager.get_user_points(user_id)
        await update.message.reply_text(f"💎 Твой баланс: {points} поинтов")

    async def meetup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /meetup (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        # Обновляем статусы митапов перед показом меню
        self.meetup_manager.update_meetup_statuses()

        keyboard = [
            [InlineKeyboardButton("➕ Добавить митап",
                                  callback_data="meetup_add")],
            [InlineKeyboardButton("✏️ Редактировать митап",
                                  callback_data="meetup_edit")],
            [InlineKeyboardButton("🗑️ Удалить митап",
                                  callback_data="meetup_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎯 Управление митапами\n\nВыберите действие:",
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
            [InlineKeyboardButton("👑 Добавить админа",
                                  callback_data="admin_add")],
            [InlineKeyboardButton("✏️ Редактировать админа",
                                  callback_data="admin_edit")],
            [InlineKeyboardButton("🗑️ Удалить админа",
                                  callback_data="admin_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👑 Управление администраторами\n\nВыберите действие:",
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

        # Получаем статистику
        total_users = self.user_manager.get_total_users()
        total_meetups = self.meetup_manager.get_total_meetups()
        active_meetups = self.meetup_manager.get_active_meetups_count()

        stats_text = f"📊 Статистика коммьюнити\n\n"
        stats_text += f"👥 Всего пользователей: {total_users}\n"
        stats_text += f"🎯 Всего митапов: {total_meetups}\n"
        stats_text += f"🔄 Активных митапов: {active_meetups}\n"

        await update.message.reply_text(stats_text)

    async def update_meetups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /update_meetups (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        # Обновляем статусы митапов
        updated = self.meetup_manager.update_meetup_statuses()

        if updated:
            await update.message.reply_text("✅ Статусы митапов обновлены!")
        else:
            await update.message.reply_text("ℹ️ Статусы митапов уже актуальны.")

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /users (только для админов)"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text(
                message_manager.get_error_message("permission_denied")
            )
            return

        # Получаем всех пользователей
        users = self.user_manager.get_all_users()

        if not users:
            await update.message.reply_text("📝 Пользователи не найдены")
            return

        users_text = "👥 Список пользователей:\n\n"

        for user in users:
            users_text += f"👤 {user.get('name', 'Не указано')} - {user.get('role', 'user')}\n"

        await update.message.reply_text(users_text)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()

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
            await self.execute_meetup_deletion(query, context, meetup_id)
        elif query.data == "cancel_delete":
            await query.edit_message_text("❌ Удаление отменено.")
        # Добавить другие обработчики по мере необходимости

    async def start_meetup_creation(self, query, context):
        """Начинает процесс создания митапа"""
        # Сохраняем данные для создания митапа
        context.user_data['creating_meetup'] = True
        context.user_data['meetup_step'] = 'name'

        await query.edit_message_text(
            "🎯 Создание нового митапа\n\nВведите название митапа:"
        )

    async def handle_meetup_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик для создания митапа пошагово"""
        if not context.user_data.get('creating_meetup'):
            return

        step = context.user_data.get('meetup_step', 'name')
        text = update.message.text

        if step == 'name':
            context.user_data['meetup_name'] = text
            context.user_data['meetup_step'] = 'date'
            await update.message.reply_text("📅 Введите дату митапа (формат: YYYY-MM-DD):")

        elif step == 'date':
            context.user_data['meetup_date'] = text
            context.user_data['meetup_step'] = 'start_time'
            await update.message.reply_text("🕐 Введите время начала (формат: HH:MM):")

        elif step == 'start_time':
            context.user_data['meetup_time_start'] = text
            context.user_data['meetup_step'] = 'end_time'
            await update.message.reply_text("🕐 Введите время окончания (формат: HH:MM):")

        elif step == 'end_time':
            context.user_data['meetup_time_end'] = text
            context.user_data['meetup_step'] = 'location'
            await update.message.reply_text("📍 Введите место проведения:")

        elif step == 'location':
            context.user_data['meetup_location'] = text
            context.user_data['meetup_step'] = 'capacity'
            await update.message.reply_text("👥 Введите максимальное количество участников:")

        elif step == 'capacity':
            try:
                capacity = int(text)
                context.user_data['meetup_capacity'] = capacity
                context.user_data['meetup_step'] = 'presentations'
                await update.message.reply_text("📝 Введите описание докладов (или 'нет' если докладов не будет):")
            except ValueError:
                await update.message.reply_text("❌ Пожалуйста, введите число. Попробуйте снова:")

        elif step == 'presentations':
            presentations = text if text.lower() != 'нет' else ""

            # Собираем данные митапа
            meetup_data = {
                'name': context.user_data['meetup_name'],
                'date': context.user_data['meetup_date'],
                'start_time': context.user_data['meetup_time_start'],
                'end_time': context.user_data['meetup_time_end'],
                'location': context.user_data['meetup_location'],
                'capacity': context.user_data['meetup_capacity'],
                'description': presentations
            }

            # Валидируем данные
            validation = self.meetup_manager.validate_meetup_data(meetup_data)
            if not validation['valid']:
                error_text = "❌ Ошибки в данных:\n"
                for error in validation['errors']:
                    error_text += f"• {error}\n"
                await update.message.reply_text(error_text)
                # Сбрасываем к началу
                context.user_data['meetup_step'] = 'name'
                await update.message.reply_text("🎯 Введите название митапа заново:")
                return

            # Создаём митап
            result = self.meetup_manager.create_meetup_interactive(meetup_data)

            if result['success']:
                success_text = "✅ Митап успешно создан!\n\n"
                success_text += f"🎯 Название: {meetup_data['name']}\n"
                success_text += f"📅 Дата: {meetup_data['date']}\n"
                success_text += f"🕐 Время: {meetup_data['start_time']} - {meetup_data['end_time']}\n"
                success_text += f"📍 Место: {meetup_data['location']}\n"
                success_text += f"👥 Вместимость: {meetup_data['capacity']}\n"

                if presentations:
                    success_text += f"📝 Доклады: {presentations}\n"

                await update.message.reply_text(success_text)
            else:
                await update.message.reply_text(f"❌ Ошибка создания митапа: {result['error']}")

            # Очищаем данные
            context.user_data.clear()

    async def handle_meetup_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Маршрутизатор для обработки текста при создании/редактировании митапов"""
        if context.user_data.get('creating_meetup'):
            await self.handle_meetup_creation(update, context)
        elif context.user_data.get('editing_meetup'):
            await self.handle_meetup_editing(update, context)
        # Если ни одно состояние не активно, игнорируем сообщение

    async def handle_meetup_editing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик для редактирования митапа пошагово"""
        if not context.user_data.get('editing_meetup'):
            return

        text = update.message.text

        if text.lower() == 'отмена':
            await update.message.reply_text("❌ Редактирование отменено.")
            context.user_data.clear()
            return

        step = context.user_data.get('edit_step', 'name')
        meetup_id = context.user_data.get('editing_meetup_id')
        original_meetup = context.user_data.get('original_meetup')

        if step == 'name':
            if text.strip():
                context.user_data['new_name'] = text
                context.user_data['edit_step'] = 'date'
                await update.message.reply_text(
                    f"📅 Текущая дата: {original_meetup['date']}\n"
                    "Введите новую дату (формат: YYYY-MM-DD) или 'пропустить':"
                )
            else:
                await update.message.reply_text("❌ Название не может быть пустым. Попробуйте снова:")

        elif step == 'date':
            if text.lower() == 'пропустить':
                context.user_data['new_date'] = original_meetup['date']
            else:
                context.user_data['new_date'] = text
            context.user_data['edit_step'] = 'start_time'
            await update.message.reply_text(
                f"🕐 Текущее время начала: {original_meetup['start_time']}\n"
                "Введите новое время начала (формат: HH:MM) или 'пропустить':"
            )

        elif step == 'start_time':
            if text.lower() == 'пропустить':
                context.user_data['new_start_time'] = original_meetup['start_time']
            else:
                context.user_data['new_start_time'] = text
            context.user_data['edit_step'] = 'end_time'
            await update.message.reply_text(
                f"🕐 Текущее время окончания: {original_meetup['end_time']}\n"
                "Введите новое время окончания (формат: HH:MM) или 'пропустить':"
            )

        elif step == 'end_time':
            if text.lower() == 'пропустить':
                context.user_data['new_end_time'] = original_meetup['end_time']
            else:
                context.user_data['new_end_time'] = text
            context.user_data['edit_step'] = 'location'
            await update.message.reply_text(
                f"📍 Текущее место: {original_meetup['location']}\n"
                "Введите новое место проведения или 'пропустить':"
            )

        elif step == 'location':
            if text.lower() == 'пропустить':
                context.user_data['new_location'] = original_meetup['location']
            else:
                context.user_data['new_location'] = text
            context.user_data['edit_step'] = 'capacity'
            await update.message.reply_text(
                f"👥 Текущая вместимость: {original_meetup['capacity']}\n"
                "Введите новую вместимость или 'пропустить':"
            )

        elif step == 'capacity':
            if text.lower() == 'пропустить':
                context.user_data['new_capacity'] = original_meetup['capacity']
            else:
                try:
                    capacity = int(text)
                    context.user_data['new_capacity'] = capacity
                except ValueError:
                    await update.message.reply_text("❌ Пожалуйста, введите число. Попробуйте снова:")
                    return
            context.user_data['edit_step'] = 'description'
            await update.message.reply_text(
                f"📝 Текущее описание: {original_meetup.get('description', 'Не указано')}\n"
                "Введите новое описание или 'пропустить':"
            )

        elif step == 'description':
            if text.lower() == 'пропустить':
                context.user_data['new_description'] = original_meetup.get(
                    'description', '')
            else:
                context.user_data['new_description'] = text

            # Собираем обновленные данные
            updates = {
                'name': context.user_data['new_name'],
                'date': context.user_data['new_date'],
                'start_time': context.user_data['new_start_time'],
                'end_time': context.user_data['new_end_time'],
                'location': context.user_data['new_location'],
                'capacity': context.user_data['new_capacity'],
                'description': context.user_data['new_description']
            }

            # Валидируем данные
            validation = self.meetup_manager.validate_meetup_data(updates)
            if not validation['valid']:
                error_text = "❌ Ошибки в данных:\n"
                for error in validation['errors']:
                    error_text += f"• {error}\n"
                await update.message.reply_text(error_text)
                # Сбрасываем к началу редактирования
                context.user_data['edit_step'] = 'name'
                await update.message.reply_text("🎯 Введите название митапа заново:")
                return

            # Обновляем митап
            try:
                self.meetup_manager.update_meetup(meetup_id, updates)

                success_text = "✅ Митап успешно обновлен!\n\n"
                success_text += f"🎯 Название: {updates['name']}\n"
                success_text += f"📅 Дата: {updates['date']}\n"
                success_text += f"🕐 Время: {updates['start_time']} - {updates['end_time']}\n"
                success_text += f"📍 Место: {updates['location']}\n"
                success_text += f"👥 Вместимость: {updates['capacity']}\n"

                if updates['description']:
                    success_text += f"📝 Описание: {updates['description']}\n"

                await update.message.reply_text(success_text)
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка обновления митапа: {str(e)}")

            # Очищаем данные
            context.user_data.clear()

    async def show_meetups_for_edit(self, query, context):
        """Показывает список митапов для редактирования"""
        meetups = self.meetup_manager.get_editable_meetups()

        if not meetups:
            await query.edit_message_text("Нет митапов для редактирования.")
            return

        text = "✏️ Выберите митап для редактирования:\n\n"
        keyboard = []

        for meetup in meetups:
            keyboard.append([
                InlineKeyboardButton(
                    f"{meetup['name']} ({meetup['date']})",
                    callback_data=f"edit_meetup_{meetup['id']}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_meetups_for_delete(self, query, context):
        """Показывает список митапов для удаления"""
        meetups = self.meetup_manager.get_deletable_meetups()

        if not meetups:
            await query.edit_message_text("Нет митапов для удаления.")
            return

        text = "🗑️ Выберите митап для удаления:\n\n"
        keyboard = []

        for meetup in meetups:
            keyboard.append([
                InlineKeyboardButton(
                    f"{meetup['name']} ({meetup['date']})",
                    callback_data=f"delete_meetup_{meetup['id']}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def start_meetup_editing(self, query, context, meetup_id):
        """Начинает процесс редактирования митапа"""
        meetup = self.meetup_manager.get_meetup(meetup_id)
        if not meetup:
            await query.edit_message_text("❌ Митап не найден.")
            return

        # Сохраняем данные для редактирования
        context.user_data['editing_meetup'] = True
        context.user_data['editing_meetup_id'] = meetup_id
        context.user_data['edit_step'] = 'name'
        context.user_data['original_meetup'] = meetup

        text = f"✏️ Редактирование митапа: {meetup['name']}\n\n"
        text += f"Текущее название: {meetup['name']}\n"
        text += "Введите новое название (или 'отмена' для выхода):"

        await query.edit_message_text(text)

    async def confirm_meetup_deletion(self, query, context, meetup_id):
        """Подтверждает удаление митапа"""
        meetup = self.meetup_manager.get_meetup(meetup_id)
        if not meetup:
            await query.edit_message_text("❌ Митап не найден.")
            return

        text = f"🗑️ Подтвердите удаление митапа:\n\n"
        text += f"🎯 Название: {meetup['name']}\n"
        text += f"📅 Дата: {meetup['date']}\n"
        text += f"📍 Место: {meetup['location']}\n\n"
        text += "⚠️ Это действие нельзя отменить!"

        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить",
                                     callback_data=f"confirm_delete_{meetup_id}"),
                InlineKeyboardButton("❌ Отмена",
                                     callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)

    async def execute_meetup_deletion(self, query, context, meetup_id):
        """Выполняет удаление митапа"""
        try:
            self.meetup_manager.delete_meetup(meetup_id)
            await query.edit_message_text("✅ Митап успешно удален!")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка удаления митапа: {str(e)}")

    def setup_handlers(self):
        """Настраивает обработчики команд и сообщений"""
        # Основные команды (start handled by ConversationHandler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(
            CommandHandler("profile", self.profile_command))
        self.application.add_handler(
            CommandHandler("points", self.points_command))

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

        # Обработчики кнопок
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback))

        # Conversation handler для регистрации
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.registration_name)],
                REGISTRATION_INFO: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, self.registration_info)]
            },
            fallbacks=[]
        )
        self.application.add_handler(conv_handler)

        # Обработчик для создания и редактирования митапов (перехватывает все текстовые сообщения)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND,
                           self.handle_meetup_text)
        )

    async def run(self):
        """Запускает бота"""
        try:
            # Отключаем прокси для этого бота
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

            logger.info("Бот запущен успешно!")

            # Держим бота запущенным - в v20 используем asyncio.Event
            stop_event = asyncio.Event()
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")

        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
        finally:
            if self.application:
                try:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                except Exception as e:
                    logger.error(f"Ошибка при остановке: {e}")


async def main():
    """Главная функция"""
    bot = GR2Bot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
