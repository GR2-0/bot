"""
Модуль для проверки участия пользователей в группах Telegram
"""
from typing import List, Dict, Optional
from telegram import Bot
from telegram.error import TelegramError
from config import config


class GroupChecker:
    """Класс для проверки участия пользователей в группах"""

    def __init__(self):
        self.bot = None
        self.community_group_id = config.get_community_group_id()
        self.admin_group_id = config.get_admin_group_id()

    async def initialize_bot(self, bot_token: str):
        """Инициализирует бота для проверки групп"""
        try:
            self.bot = Bot(token=bot_token)
        except Exception as e:
            print(f"Ошибка инициализации бота: {e}")

    async def is_user_in_community(self, user_id: str) -> bool:
        """
        Проверяет, состоит ли пользователь в группе коммьюнити

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            True если пользователь в группе, False иначе
        """
        print(f"DEBUG: Checking if user {user_id} is in community group "
              f"{self.community_group_id}")
        print(f"DEBUG: Bot initialized: {self.bot is not None}")

        if not self.bot or not self.community_group_id:
            print("DEBUG: Bot not initialized or no community group ID")
            return False

        try:
            # Получаем информацию о пользователе в группе
            member = await self.bot.get_chat_member(
                chat_id=self.community_group_id,
                user_id=int(user_id)
            )

            print(f"DEBUG: User status in group: {member.status}")

            # Проверяем, что пользователь не покинул группу
            return member.status not in ['left', 'kicked']

        except TelegramError as e:
            if ("User not found" in str(e) or
                    "Chat not found" in str(e)):
                print(f"DEBUG: User not found in group: {e}")
                return False
            else:
                print(f"Ошибка проверки пользователя в группе: {e}")
                return False
        except Exception as e:
            print(f"Неожиданная ошибка при проверке группы: {e}")
            return False

    async def is_user_in_admin_group(self, user_id: str) -> bool:
        """
        Проверяет, состоит ли пользователь в админской группе

        Args:
            user_id: ID пользователя в Telegram

        Returns:
            True если пользователь в админской группе, False иначе
        """
        if not self.bot or not self.admin_group_id:
            return False

        try:
            member = await self.bot.get_chat_member(
                chat_id=self.admin_group_id,
                user_id=int(user_id)
            )

            return member.status not in ['left', 'kicked']

        except TelegramError as e:
            if "User not found" in str(e) or "Chat not found" in str(e):
                return False
            else:
                print(f"Ошибка проверки пользователя в админской группе: {e}")
                return False
        except Exception as e:
            print(f"Неожиданная ошибка при проверке админской группы: {e}")
            return False

    async def get_group_members(self, group_id: str, limit: int = 100) -> List[Dict]:
        """
        Получает список участников группы

        Args:
            group_id: ID группы
            limit: Максимальное количество участников

        Returns:
            Список участников группы
        """
        if not self.bot:
            return []

        try:
            members = []
            async for member in self.bot.get_chat_members(chat_id=group_id):
                if len(members) >= limit:
                    break

                members.append({
                    'user_id': str(member.user.id),
                    'username': member.user.username,
                    'first_name': member.user.first_name,
                    'last_name': member.user.last_name,
                    'status': member.status
                })

            return members

        except TelegramError as e:
            print(f"Ошибка получения участников группы: {e}")
            return []
        except Exception as e:
            print(f"Неожиданная ошибка при получении участников: {e}")
            return []

    async def get_community_members(self, limit: int = 100) -> List[Dict]:
        """Получает список участников группы коммьюнити"""
        return await self.get_group_members(self.community_group_id, limit)

    async def get_admin_group_members(self, limit: int = 100) -> List[Dict]:
        """Получает список участников админской группы"""
        return await self.get_admin_group_members(self.admin_group_id, limit)

    async def check_user_status_in_group(self, user_id: str, group_id: str) -> Optional[str]:
        """
        Проверяет статус пользователя в группе

        Args:
            user_id: ID пользователя
            group_id: ID группы

        Returns:
            Статус пользователя или None если не найден
        """
        if not self.bot:
            return None

        try:
            member = await self.bot.get_chat_member(
                chat_id=group_id,
                user_id=int(user_id)
            )

            return member.status

        except TelegramError as e:
            if ("User not found" in str(e) or
                    "Chat not found" in str(e)):
                return None
            else:
                print(f"Ошибка проверки статуса пользователя: {e}")
                return None
        except Exception as e:
            print(f"Неожиданная ошибка при проверке статуса: {e}")
            return None

    async def get_group_info(self, group_id: str) -> Optional[Dict]:
        """
        Получает информацию о группе

        Args:
            group_id: ID группы

        Returns:
            Информация о группе или None
        """
        if not self.bot:
            return None

        try:
            chat = await self.bot.get_chat(chat_id=group_id)

            member_count = (chat.member_count
                            if hasattr(chat, 'member_count') else None)
            description = (chat.description
                           if hasattr(chat, 'description') else None)

            return {
                'id': str(chat.id),
                'title': chat.title,
                'type': chat.type,
                'member_count': member_count,
                'description': description
            }

        except TelegramError as e:
            print(f"Ошибка получения информации о группе: {e}")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка при получении информации о группе: {e}")
            return None

    async def get_community_info(self) -> Optional[Dict]:
        """Получает информацию о группе коммьюнити"""
        return await self.get_group_info(self.community_group_id)

    async def get_admin_group_info(self) -> Optional[Dict]:
        """Получает информацию об админской группе"""
        return await self.get_group_info(self.admin_group_id)

    async def cleanup(self):
        """Очищает ресурсы"""
        if self.bot:
            await self.bot.close()
