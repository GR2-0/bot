"""
Модуль для управления пользователями
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class UserManager:
    """Класс для управления пользователями"""
    
    def __init__(self, users_file: str = "data/private/users/users.json"):
        self.users_file = Path(users_file)
        self.users = {}
        self.load_users()
    
    def load_users(self):
        """Загружает пользователей из файла"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            else:
                # Создаём директорию если её нет
                self.users_file.parent.mkdir(parents=True, exist_ok=True)
                self.users = {}
                self.save_users()
        except Exception as e:
            print(f"Ошибка загрузки пользователей: {e}")
            self.users = {}
    
    def save_users(self):
        """Сохраняет пользователей в файл"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения пользователей: {e}")
    
    def user_exists(self, user_id: str) -> bool:
        """Проверяет, существует ли пользователь"""
        return user_id in self.users
    
    def create_user(self, user_data: Dict):
        """Создаёт нового пользователя"""
        user_id = user_data['id']
        if self.user_exists(user_id):
            raise ValueError(f"Пользователь {user_id} уже существует")
        
        # Добавляем недостающие поля
        user_data.setdefault('registration_date', datetime.now().strftime('%Y-%m-%d'))
        user_data.setdefault('role', 'user')
        user_data.setdefault('points', 0)
        user_data.setdefault('info', '')
        
        self.users[user_id] = user_data
        self.save_users()
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Возвращает данные пользователя"""
        return self.users.get(user_id)
    
    def update_user(self, user_id: str, updates: Dict):
        """Обновляет данные пользователя"""
        if not self.user_exists(user_id):
            raise ValueError(f"Пользователь {user_id} не найден")
        
        self.users[user_id].update(updates)
        self.save_users()
    
    def delete_user(self, user_id: str):
        """Удаляет пользователя"""
        if user_id in self.users:
            del self.users[user_id]
            self.save_users()
    
    def is_admin(self, user_id: str) -> bool:
        """Проверяет, является ли пользователь админом"""
        user = self.get_user(user_id)
        return user and user.get('role') == 'admin'
    
    def add_admin(self, user_id: str):
        """Добавляет пользователя как админа"""
        if not self.user_exists(user_id):
            raise ValueError(f"Пользователь {user_id} не найден")
        
        self.users[user_id]['role'] = 'admin'
        self.save_users()
    
    def remove_admin(self, user_id: str):
        """Убирает права админа у пользователя"""
        if not self.user_exists(user_id):
            raise ValueError(f"Пользователь {user_id} не найден")
        
        self.users[user_id]['role'] = 'user'
        self.save_users()
    
    def get_all_users(self) -> List[Dict]:
        """Возвращает список всех пользователей"""
        return list(self.users.values())
    
    def get_users_by_role(self, role: str) -> List[Dict]:
        """Возвращает пользователей по роли"""
        return [user for user in self.users.values() if user.get('role') == role]
    
    def get_total_users(self) -> int:
        """Возвращает общее количество пользователей"""
        return len(self.users)
    
    def get_active_users(self) -> List[Dict]:
        """Возвращает активных пользователей (не dead)"""
        return [user for user in self.users.values() if user.get('role') != 'dead']
    
    def mark_user_dead(self, user_id: str):
        """Отмечает пользователя как неактивного"""
        if self.user_exists(user_id):
            self.users[user_id]['role'] = 'dead'
            self.save_users()
    
    def get_user_stats(self) -> Dict:
        """Возвращает статистику пользователей"""
        total = len(self.users)
        admins = len([u for u in self.users.values() if u.get('role') == 'admin'])
        dead = len([u for u in self.users.values() if u.get('role') == 'dead'])
        active = total - dead
        
        return {
            'total': total,
            'admins': admins,
            'active': active,
            'dead': dead
        }

