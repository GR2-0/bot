"""
Модуль для загрузки текстовых сообщений бота
"""
import json
from pathlib import Path
from typing import Dict, Any


class MessageManager:
    """Класс для управления сообщениями бота"""
    
    def __init__(self, messages_dir: str = "data/public/messages"):
        self.messages_dir = Path(messages_dir)
        self.messages = {}
        self.load_messages()
    
    def load_messages(self):
        """Загружает все файлы сообщений"""
        try:
            messages_path = self.messages_dir / "bot_messages.json"
            if messages_path.exists():
                with open(messages_path, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки сообщений: {e}")
            self.messages = {}
    
    def get_message(self, category: str, key: str, **kwargs) -> str:
        """
        Возвращает сообщение по категории и ключу
        
        Args:
            category: Категория сообщения (welcome, registration, meetup, etc.)
            key: Ключ сообщения
            **kwargs: Параметры для форматирования сообщения
        
        Returns:
            Отформатированное сообщение или пустая строка
        """
        try:
            message = self.messages.get(category, {}).get(key, "")
            if message and kwargs:
                return message.format(**kwargs)
            return message
        except Exception as e:
            print(f"Ошибка получения сообщения {category}.{key}: {e}")
            return ""
    
    def get_welcome_message(self, is_new_user: bool = True) -> str:
        """Возвращает приветственное сообщение"""
        key = "new_user" if is_new_user else "existing_user"
        return self.get_message("welcome", key)
    
    def get_registration_message(self, key: str, **kwargs) -> str:
        """Возвращает сообщение регистрации"""
        return self.get_message("registration", key, **kwargs)
    
    def get_meetup_message(self, key: str, **kwargs) -> str:
        """Возвращает сообщение митапа"""
        return self.get_message("meetup", key, **kwargs)
    
    def get_admin_message(self, key: str, **kwargs) -> str:
        """Возвращает админское сообщение"""
        return self.get_message("admin", key, **kwargs)
    
    def get_feedback_message(self, key: str, **kwargs) -> str:
        """Возвращает сообщение фидбека"""
        return self.get_message("feedback", key, **kwargs)
    
    def get_error_message(self, key: str, **kwargs) -> str:
        """Возвращает сообщение об ошибке"""
        return self.get_message("errors", key, **kwargs)
    
    def get_help_message(self, is_admin: bool = False) -> str:
        """Возвращает справочное сообщение"""
        key = "admin" if is_admin else "user"
        return self.get_message("help", key)
    
    def reload_messages(self):
        """Перезагружает сообщения"""
        self.load_messages()


# Глобальный экземпляр менеджера сообщений
message_manager = MessageManager()

