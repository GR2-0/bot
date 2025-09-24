"""
Унифицированный модуль для управления опросами и обработки в боте
"""
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from models.user import UserManager
from models.meetup import MeetupManager
# from messages import message_manager  # Not used in unified module

logger = logging.getLogger(__name__)
MOSCOW_TZ = timezone(timedelta(hours=3))


class PollsManager:
    """Класс для управления опросами"""

    def __init__(self, config_dir: str = "data/private/polls/config",
                 results_dir: str = "data/private/polls/results"):
        self.config_dir = Path(config_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.user_manager = UserManager()
        self.meetup_manager = MeetupManager()
        self._active_polls = {}  # poll_id -> results_file_path

    def _now_moscow(self) -> datetime:
        return datetime.now(MOSCOW_TZ)

    def _iso_moscow(self) -> str:
        return self._now_moscow().isoformat()

    def list_poll_configs(self) -> List[str]:
        """Возвращает список доступных poll_id"""
        if not self.config_dir.exists():
            return []
        return [f.stem for f in self.config_dir.glob("*.json")]

    def load_poll_config(self, poll_id: str) -> Dict[str, Any]:
        """Загружает конфигурацию опроса"""
        config_path = self.config_dir / f"{poll_id}.json"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Конфигурация опроса {poll_id} не найдена")

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def is_poll_active(self, poll_id: str) -> bool:
        """Проверяет, активен ли опрос"""
        return poll_id in self._active_polls

    def start_poll(self, poll_id: str, started_by: str) -> Dict[str, Any]:
        """Запускает опрос"""
        if self.is_poll_active(poll_id):
            raise ValueError(f"Опрос {poll_id} уже активен")

        config = self.load_poll_config(poll_id)
        target_user_ids = self._get_target_users(config)

        # Создаем файл результатов
        start_date = self._iso_moscow().split("T")[0]
        results_path = self.results_dir / f"{poll_id}_{start_date}.json"

        results_doc = {
            "poll_id": config["id"],
            "poll_title": config["title"],
            "started_at": self._iso_moscow(),
            "ended_at": None,
            "total_responses": 0,
            "target_audience": {
                "type": config["target_audience"]["type"],
                "meetup_id": config["target_audience"].get("meetup_id"),
                "total_eligible": len(target_user_ids),
            },
            "responses": [],
        }

        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results_doc, f, ensure_ascii=False, indent=2)

        self._active_polls[poll_id] = results_path

        return {
            "results_path": str(results_path),
            "eligible_user_ids": target_user_ids
        }

    def record_response(self, poll_id: str, user_id: str,
                        answers: Dict[str, Any]) -> Dict[str, Any]:
        """Записывает ответ пользователя"""
        config = self.load_poll_config(poll_id)
        settings = config.get("settings", {})

        # Определяем путь к файлу результатов
        if poll_id in self._active_polls:
            results_path = self._active_polls[poll_id]
            results_doc = self._read_json(results_path)
        else:
            # Создаем или используем файл для неактивного опроса
            start_date = self._now_moscow().strftime('%Y-%m-%d')
            results_path = self.results_dir / f"{poll_id}_{start_date}.json"

            if results_path.exists():
                results_doc = self._read_json(results_path)
            else:
                results_doc = {
                    "poll_id": poll_id,
                    "poll_title": config["title"],
                    "started_at": self._iso_moscow(),
                    "ended_at": None,
                    "total_responses": 0,
                    "target_audience": {
                        "type": config["target_audience"]["type"],
                        "meetup_id": config["target_audience"].get("meetup_id"),
                        "total_eligible": 0,
                    },
                    "responses": [],
                }

        # Проверяем повторные ответы
        if not settings.get("allow_multiple_responses", False):
            existing_responses = results_doc.get("responses", [])
            if any(r.get("user_id") == user_id for r in existing_responses):
                raise ValueError(
                    "Повторные ответы запрещены для этого опроса")

        # Валидируем ответы
        self._validate_answers(config, answers)

        # Добавляем ответ
        response_entry = {
            "response_id": f"resp_{uuid.uuid4().hex[:8]}",
            "user_id": None if settings.get("anonymous", False) else user_id,
            "submitted_at": self._iso_moscow(),
            "answers": answers,
        }

        results_doc["responses"].append(response_entry)
        results_doc["total_responses"] = len(results_doc["responses"])

        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results_doc, f, ensure_ascii=False, indent=2)

        return response_entry

    def finalize_poll(self, poll_id: str) -> Dict[str, Any]:
        """Завершает опрос"""
        if poll_id not in self._active_polls:
            raise ValueError("Опрос не активен")

        results_path = self._active_polls[poll_id]
        results_doc = self._read_json(results_path)
        results_doc["ended_at"] = self._iso_moscow()

        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results_doc, f, ensure_ascii=False, indent=2)

        del self._active_polls[poll_id]
        return results_doc

    def validate_complete_answers(self, config: Dict[str, Any],
                                  answers: Dict[str, Any]) -> None:
        """Валидирует полные ответы"""
        self._validate_answers(config, answers, validate_required=True)

    def _get_target_users(self, config: Dict[str, Any]) -> List[str]:
        """Получает список целевых пользователей"""
        target_type = config["target_audience"]["type"]

        if target_type == "all_users":
            return self.user_manager.get_all_user_ids()
        elif target_type == "meetup_attendees":
            meetup_id = config["target_audience"]["meetup_id"]
            return self.meetup_manager.get_meetup_attendees(meetup_id)
        else:
            raise ValueError(
                f"Неизвестный тип целевой аудитории: {target_type}")

    def _validate_answers(self, config: Dict[str, Any],
                          answers: Dict[str, Any],
                          validate_required: bool = False) -> None:
        """Валидирует ответы пользователя"""
        questions = config.get("questions", [])

        for question in questions:
            qid = question["id"]
            qtype = question["type"]
            required = question.get("required", False)

            if required and validate_required and qid not in answers:
                raise ValueError(f"Обязательный вопрос {qid} не отвечен")

            if qid in answers:
                answer = answers[qid]

                if qtype == "single_choice":
                    if answer not in question["options"]:
                        raise ValueError(
                            f"Недопустимый ответ на вопрос {qid}")
                elif qtype == "text":
                    max_length = question.get("max_length")
                    if max_length and len(str(answer)) > max_length:
                        raise ValueError(
                            f"Ответ на вопрос {qid} слишком длинный")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """Читает JSON файл"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


class BotPollsHandlers:
    """Обработчики опросов для бота"""

    def __init__(self, user_manager, application):
        self.user_manager = user_manager
        self.application = application
        self.polls_manager = PollsManager()

    async def polls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /polls - управление опросами"""
        user_id = str(update.effective_user.id)

        if not self.user_manager.is_admin(user_id):
            await update.message.reply_text("❌ Доступ запрещен")
            return

        available_polls = self.polls_manager.list_poll_configs()
        if not available_polls:
            await update.message.reply_text("📝 Конфигурации опросов не найдены")
            return

        # Показываем список опросов
        keyboard = []
        for poll_id in available_polls:
            status = "🟢 Активен" if self.polls_manager.is_poll_active(
                poll_id) else "⚪ Неактивен"
            keyboard.append([InlineKeyboardButton(
                f"{poll_id} {status}",
                callback_data=f"poll_select_{poll_id}"
            )])

        keyboard.append([InlineKeyboardButton(
            "📊 Активные опросы", callback_data="polls_active")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 Управление опросами\n\nВыберите опрос для управления:",
            reply_markup=reply_markup
        )

    async def handle_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback'ов опросов"""
        query = update.callback_query
        await query.answer()

        if query.data.startswith("poll_select_"):
            poll_id = query.data.replace("poll_select_", "")
            await self._show_poll_actions(query, context, poll_id)
        elif query.data.startswith("poll_start_"):
            data_parts = query.data.split('_')
            if len(data_parts) >= 4:
                poll_id = '_'.join(data_parts[2:-1])
                user_id = data_parts[-1]
                await self._start_poll_for_user(update, context, poll_id, user_id)
        elif query.data.startswith("poll_answer_"):
            await self._handle_poll_answer(update, context)
        elif query.data == "polls_active":
            await self._show_active_polls(query, context)
        elif query.data.startswith("poll_stop_"):
            poll_id = query.data.replace("poll_stop_", "")
            await self._stop_poll(query, context, poll_id)
        elif query.data.startswith("poll_launch_"):
            poll_id = query.data.replace("poll_launch_", "")
            await self._launch_poll(query, context, poll_id)

    async def _show_poll_actions(self, query, context, poll_id: str):
        """Показывает действия для опроса"""
        try:
            config = self.polls_manager.load_poll_config(poll_id)
            is_active = self.polls_manager.is_poll_active(poll_id)

            keyboard = []
            if is_active:
                keyboard.append([InlineKeyboardButton(
                    "🛑 Остановить", callback_data=f"poll_stop_{poll_id}")])
            else:
                keyboard.append([InlineKeyboardButton(
                    "🚀 Запустить", callback_data=f"poll_launch_{poll_id}")])

            keyboard.append([InlineKeyboardButton(
                "⬅️ Назад", callback_data="polls_back")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📋 {config['title']}\n\n"
                f"Статус: {'🟢 Активен' if is_active else '⚪ Неактивен'}\n"
                f"Вопросов: {len(config.get('questions', []))}",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка показа действий опроса: {e}")
            await query.edit_message_text("❌ Ошибка загрузки опроса")

    async def _launch_poll(self, query, context, poll_id: str):
        """Запускает опрос"""
        try:
            result = self.polls_manager.start_poll(
                poll_id, str(query.from_user.id))
            user_ids = result["eligible_user_ids"]

            # Отправляем опрос пользователям
            sent_count = 0
            for user_id in user_ids:
                try:
                    config = self.polls_manager.load_poll_config(poll_id)
                    keyboard = [[InlineKeyboardButton(
                        "📝 Начать опрос",
                        callback_data=f"poll_start_{poll_id}_{user_id}"
                    )]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=f"📋 {config['title']}\n\n{config.get('description', '')}\n\nПожалуйста, ответьте на вопросы ниже:",
                        reply_markup=reply_markup
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        f"Ошибка отправки опроса пользователю {user_id}: {e}")

            await query.edit_message_text(
                f"✅ Опрос '{poll_id}' запущен!\n"
                f"📊 Целевая аудитория: {len(user_ids)} пользователей\n"
                f"📁 Результаты: {result['results_path']}\n"
                f"📤 Сообщения отправлены {sent_count} пользователям"
            )
        except Exception as e:
            logger.error(f"Ошибка запуска опроса: {e}")
            await query.edit_message_text("❌ Ошибка запуска опроса")

    async def _stop_poll(self, query, context, poll_id: str):
        """Останавливает опрос"""
        try:
            if not self.polls_manager.is_poll_active(poll_id):
                await query.edit_message_text("❌ Опрос не активен")
                return

            result = self.polls_manager.finalize_poll(poll_id)
            await query.edit_message_text(
                f"✅ Опрос '{poll_id}' остановлен!\n"
                f"📊 Всего ответов: {result['total_responses']}"
            )
        except Exception as e:
            logger.error(f"Ошибка остановки опроса: {e}")
            await query.edit_message_text("❌ Ошибка остановки опроса")

    async def _show_active_polls(self, query, context):
        """Показывает активные опросы"""
        active_polls = [
            poll_id for poll_id in self.polls_manager.list_poll_configs()
            if self.polls_manager.is_poll_active(poll_id)
        ]

        if not active_polls:
            await query.edit_message_text("📊 Активных опросов нет")
            return

        text = "📊 Активные опросы:\n\n"
        for poll_id in active_polls:
            try:
                config = self.polls_manager.load_poll_config(poll_id)
                text += f"• {config['title']} ({poll_id})\n"
            except:
                text += f"• {poll_id}\n"

        keyboard = [[InlineKeyboardButton(
            "⬅️ Назад", callback_data="polls_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def _start_poll_for_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   poll_id: str, user_id: str):
        """Начинает опрос для пользователя"""
        query = update.callback_query
        await query.answer()

        try:
            config = self.polls_manager.load_poll_config(poll_id)
            questions = config.get('questions', [])

            if not questions:
                await query.edit_message_text("❌ В опросе нет вопросов")
                return

            # Сохраняем данные опроса
            context.user_data['current_poll'] = poll_id
            context.user_data['poll_questions'] = questions
            context.user_data['poll_answers'] = {}
            context.user_data['current_question_index'] = 0
            context.user_data['user_id'] = user_id

            # Показываем первый вопрос
            await self._show_poll_question(query, context, 0)

        except Exception as e:
            logger.error(f"Ошибка начала опроса: {e}")
            await query.edit_message_text("❌ Ошибка загрузки опроса")

    async def _show_poll_question(self, query, context, question_index: int):
        """Показывает вопрос опроса"""
        try:
            questions = context.user_data.get('poll_questions', [])
            if question_index >= len(questions):
                # Опрос завершен
                await self._save_user_response(query, context)
                return

            question = questions[question_index]
            qtype = question['type']

            if qtype == 'single_choice':
                keyboard = []
                for option in question['options']:
                    keyboard.append([InlineKeyboardButton(
                        option,
                        callback_data=f"poll_answer_{question['id']}_{option}"
                    )])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    f"❓ {question['text']}\n\nВыберите вариант ответа:",
                    reply_markup=reply_markup
                )
            elif qtype == 'text':
                context.user_data['waiting_for_text'] = question['id']
                if query:
                    await query.edit_message_text(
                        f"❓ {question['text']}\n\nВведите ваш ответ:"
                    )
                else:
                    # Для текстовых ответов отправляем новое сообщение через update
                    # Это будет обработано в handle_poll_text_response
                    pass
        except Exception as e:
            logger.error(f"Ошибка показа вопроса: {e}")

    async def _handle_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ответ на вопрос"""
        query = update.callback_query
        await query.answer()

        try:
            data_parts = query.data.split('_')
            if len(data_parts) >= 4:
                question_id = data_parts[2]
                answer = '_'.join(data_parts[3:])

                # Сохраняем ответ
                answers = context.user_data.get('poll_answers', {})
                answers[question_id] = answer
                context.user_data['poll_answers'] = answers

                # Переходим к следующему вопросу
                current_index = context.user_data.get(
                    'current_question_index', 0)
                next_index = current_index + 1
                context.user_data['current_question_index'] = next_index

                await self._show_poll_question(query, context, next_index)
        except Exception as e:
            logger.error(f"Ошибка обработки ответа: {e}")

    async def handle_poll_text_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает текстовый ответ"""
        if 'waiting_for_text' not in context.user_data:
            return

        try:
            question_id = context.user_data['waiting_for_text']
            text_answer = update.message.text

            # Проверяем длину ответа
            questions = context.user_data.get('poll_questions', [])
            current_index = context.user_data.get('current_question_index', 0)
            question = questions[current_index]
            max_length = question.get('max_length')

            if max_length and len(text_answer) > max_length:
                await update.message.reply_text(f"❌ Ответ слишком длинный. Максимум {max_length} символов.")
                return

            # Сохраняем ответ
            answers = context.user_data.get('poll_answers', {})
            answers[question_id] = text_answer
            context.user_data['poll_answers'] = answers

            # Убираем флаг ожидания
            del context.user_data['waiting_for_text']

            # Переходим к следующему вопросу
            next_index = current_index + 1
            context.user_data['current_question_index'] = next_index

            # Показываем следующий вопрос
            await self._show_next_question_for_text(update, context, next_index)

        except Exception as e:
            logger.error(f"Ошибка обработки текстового ответа: {e}")

    async def _show_next_question_for_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int):
        """Показывает следующий вопрос для текстовых ответов"""
        try:
            questions = context.user_data.get('poll_questions', [])
            if question_index >= len(questions):
                # Опрос завершен - сохраняем ответы
                await self._save_user_response_for_text(update, context)
                return

            question = questions[question_index]
            qtype = question['type']

            if qtype == 'single_choice':
                # Для single_choice вопросов отправляем сообщение с кнопками
                keyboard = []
                for option in question['options']:
                    keyboard.append([InlineKeyboardButton(
                        option,
                        callback_data=f"poll_answer_{question['id']}_{option}"
                    )])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"❓ {question['text']}\n\nВыберите вариант ответа:",
                    reply_markup=reply_markup
                )
            elif qtype == 'text':
                # Для текстовых вопросов устанавливаем флаг ожидания
                context.user_data['waiting_for_text'] = question['id']
                await update.message.reply_text(
                    f"❓ {question['text']}\n\nВведите ваш ответ:"
                )
        except Exception as e:
            logger.error(f"Ошибка показа следующего вопроса: {e}")

    async def _save_user_response_for_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохраняет ответы пользователя для текстовых ответов"""
        try:
            poll_id = context.user_data.get('current_poll')
            user_id = context.user_data.get('user_id')
            answers = context.user_data.get('poll_answers', {})

            if not poll_id or not user_id:
                await update.message.reply_text("❌ Ошибка: данные опроса не найдены")
                return

            # Валидируем и сохраняем ответы
            config = self.polls_manager.load_poll_config(poll_id)
            self.polls_manager.validate_complete_answers(config, answers)
            response = self.polls_manager.record_response(
                poll_id, user_id, answers)

            # Очищаем данные пользователя
            for key in ['current_poll', 'poll_questions', 'poll_answers',
                        'current_question_index', 'waiting_for_text', 'user_id']:
                context.user_data.pop(key, None)

            await update.message.reply_text(
                "✅ Спасибо! Ваши ответы сохранены.\n\n"
                "Ваше мнение поможет нам улучшить качество мероприятий!"
            )

        except Exception as e:
            logger.error(f"Ошибка сохранения ответов: {e}")
            await update.message.reply_text("❌ Ошибка сохранения ответов")

    async def _save_user_response(self, query, context):
        """Сохраняет ответы пользователя"""
        try:
            poll_id = context.user_data.get('current_poll')
            user_id = context.user_data.get('user_id')
            answers = context.user_data.get('poll_answers', {})

            if not poll_id or not user_id:
                if query:
                    await query.edit_message_text("❌ Ошибка: данные опроса не найдены")
                return

            # Валидируем и сохраняем ответы
            config = self.polls_manager.load_poll_config(poll_id)
            self.polls_manager.validate_complete_answers(config, answers)
            response = self.polls_manager.record_response(
                poll_id, user_id, answers)

            # Очищаем данные пользователя
            for key in ['current_poll', 'poll_questions', 'poll_answers',
                        'current_question_index', 'waiting_for_text', 'user_id']:
                context.user_data.pop(key, None)

            if query:
                await query.edit_message_text(
                    "✅ Спасибо! Ваши ответы сохранены.\n\n"
                    "Ваше мнение поможет нам улучшить качество мероприятий!"
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ Спасибо! Ваши ответы сохранены.\n\n"
                         "Ваше мнение поможет нам улучшить качество мероприятий!"
                )

        except Exception as e:
            logger.error(f"Ошибка сохранения ответов: {e}")
            if query:
                await query.edit_message_text("❌ Ошибка сохранения ответов")


# Создаем глобальный экземпляр для обратной совместимости
polls_manager = PollsManager()
