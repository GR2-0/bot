"""
Основной модуль бота GR2-0 Community Bot
"""
import asyncio
import logging
from datetime import datetime, time
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
            'registration_date': datetime.now().strftime('%Y-%m-%d'),
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
        # Добавить другие обработчики по мере необходимости

    async def start_meetup_creation(self, query, context):
        """Начинает процесс создания митапа"""
        await query.edit_message_text(
            "🎯 Создание нового митапа\n\nВведите название митапа:"
        )
        return MEETUP_CREATION_NAME

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
