"""
Модуль конфигурации для загрузки настроек бота
"""
import json
import os
from typing import Dict, Any
from pathlib import Path


class Config:
    """Класс для управления конфигурацией бота"""
    
    def __init__(self, config_dir: str = "data/private/config"):
        self.config_dir = Path(config_dir)
        self.bot_config = {}
        self.points_config = {}
        self.community_config = {}
        self.load_all_configs()
    
    def load_all_configs(self):
        """Загружает все конфигурационные файлы"""
        try:
            # Загружаем конфигурацию бота
            bot_config_path = self.config_dir / "bot_config.json"
            if bot_config_path.exists():
                with open(bot_config_path, 'r', encoding='utf-8') as f:
                    self.bot_config = json.load(f)
            
            # Загружаем конфигурацию поинтов
            points_config_path = self.config_dir / "points_config.json"
            if points_config_path.exists():
                with open(points_config_path, 'r', encoding='utf-8') as f:
                    self.points_config = json.load(f)
            
            # Загружаем конфигурацию коммьюнити
            community_config_path = self.config_dir / "community_config.json"
            if community_config_path.exists():
                with open(community_config_path, 'r', encoding='utf-8') as f:
                    self.community_config = json.load(f)
                    
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
    
    def get_bot_token(self) -> str:
        """Возвращает токен бота"""
        return self.bot_config.get("bot", {}).get("token", "")
    
    def get_community_group_id(self) -> str:
        """Возвращает ID группы коммьюнити"""
        return self.bot_config.get("groups", {}).get("community", "")
    
    def get_admin_group_id(self) -> str:
        """Возвращает ID админской группы"""
        return self.bot_config.get("groups", {}).get("admin", "")
    
    def get_qr_interval(self) -> int:
        """Возвращает интервал генерации QR-кодов в секундах"""
        return self.bot_config.get("settings", {}).get("qr_code_interval", 10)
    
    def get_daily_check_time(self) -> str:
        """Возвращает время ежедневной проверки"""
        return self.bot_config.get("settings", {}).get("daily_check_time", "21:00")
    
    def get_feedback_hours(self) -> int:
        """Возвращает время сбора фидбека в часах"""
        return self.bot_config.get("settings", {}).get("feedback_collection_hours", 24)
    
    def get_points_for_action(self, action: str) -> int:
        """Возвращает количество поинтов за действие"""
        return self.points_config.get("actions", {}).get(action, 0)
    
    def get_feedback_min_length(self) -> int:
        """Возвращает минимальную длину ответа для получения поинтов"""
        return self.points_config.get("feedback", {}).get("min_length_for_points", 128)
    
    def get_feedback_questions(self) -> list:
        """Возвращает список вопросов для фидбека"""
        return self.points_config.get("feedback", {}).get("questions", [])
    
    def reload_configs(self):
        """Перезагружает все конфигурации"""
        self.load_all_configs()


# Глобальный экземпляр конфигурации
config = Config()

