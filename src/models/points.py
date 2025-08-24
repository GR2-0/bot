"""
Модуль для управления системой поинтов
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class PointsManager:
    """Класс для управления системой поинтов"""
    
    def __init__(self, points_file: str = "data/private/users/points.json"):
        self.points_file = Path(points_file)
        self.points = {}
        self.transactions = {}
        self.load_points()
    
    def load_points(self):
        """Загружает данные о поинтах из файла"""
        try:
            if self.points_file.exists():
                with open(self.points_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.points = data.get('points', {})
                    self.transactions = data.get('transactions', {})
            else:
                # Создаём директорию если её нет
                self.points_file.parent.mkdir(parents=True, exist_ok=True)
                self.points = {}
                self.transactions = {}
                self.save_points()
        except Exception as e:
            print(f"Ошибка загрузки поинтов: {e}")
            self.points = {}
            self.transactions = {}
    
    def save_points(self):
        """Сохраняет данные о поинтах в файл"""
        try:
            data = {
                'points': self.points,
                'transactions': self.transactions,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.points_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения поинтов: {e}")
    
    def get_user_points(self, user_id: str) -> int:
        """Возвращает количество поинтов пользователя"""
        return self.points.get(user_id, 0)
    
    def add_points(self, user_id: str, amount: int, reason: str = "Начисление"):
        """Добавляет поинты пользователю"""
        if amount <= 0:
            raise ValueError("Количество поинтов должно быть положительным")
        
        current_points = self.get_user_points(user_id)
        new_points = current_points + amount
        
        self.points[user_id] = new_points
        
        # Записываем транзакцию
        transaction_id = f"{user_id}_{datetime.now().timestamp()}"
        self.transactions[transaction_id] = {
            'user_id': user_id,
            'type': 'add',
            'amount': amount,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'balance_before': current_points,
            'balance_after': new_points
        }
        
        self.save_points()
    
    def remove_points(self, user_id: str, amount: int, reason: str = "Списание"):
        """Убирает поинты у пользователя"""
        if amount <= 0:
            raise ValueError("Количество поинтов должно быть положительным")
        
        current_points = self.get_user_points(user_id)
        if current_points < amount:
            raise ValueError("Недостаточно поинтов для списания")
        
        new_points = current_points - amount
        
        self.points[user_id] = new_points
        
        # Записываем транзакцию
        transaction_id = f"{user_id}_{datetime.now().timestamp()}"
        self.transactions[transaction_id] = {
            'user_id': user_id,
            'type': 'remove',
            'amount': amount,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'balance_before': current_points,
            'balance_after': new_points
        }
        
        self.save_points()
    
    def transfer_points(self, from_user_id: str, to_user_id: str, amount: int, reason: str = "Перевод"):
        """Переводит поинты между пользователями"""
        if amount <= 0:
            raise ValueError("Количество поинтов должно быть положительным")
        
        # Проверяем баланс отправителя
        from_user_points = self.get_user_points(from_user_id)
        if from_user_points < amount:
            raise ValueError("Недостаточно поинтов для перевода")
        
        # Выполняем перевод
        self.remove_points(from_user_id, amount, f"Перевод пользователю {to_user_id}: {reason}")
        self.add_points(to_user_id, amount, f"Перевод от пользователя {from_user_id}: {reason}")
    
    def get_user_transactions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Возвращает историю транзакций пользователя"""
        user_transactions = [
            trans for trans in self.transactions.values()
            if trans['user_id'] == user_id
        ]
        
        # Сортируем по времени (новые сначала)
        user_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return user_transactions[:limit]
    
    def get_all_transactions(self, limit: int = 100) -> List[Dict]:
        """Возвращает все транзакции"""
        all_transactions = list(self.transactions.values())
        all_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return all_transactions[:limit]
    
    def get_points_stats(self) -> Dict:
        """Возвращает статистику поинтов"""
        total_points = sum(self.points.values())
        total_users = len(self.points)
        avg_points = total_points / total_users if total_users > 0 else 0
        
        # Топ пользователей по поинтам
        top_users = sorted(
            [(user_id, points) for user_id, points in self.points.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_points': total_points,
            'total_users': total_users,
            'average_points': round(avg_points, 2),
            'top_users': top_users
        }
    
    def get_user_rank(self, user_id: str) -> Optional[int]:
        """Возвращает ранг пользователя по поинтам"""
        if user_id not in self.points:
            return None
        
        user_points = self.points[user_id]
        sorted_users = sorted(
            self.points.values(),
            reverse=True
        )
        
        try:
            return sorted_users.index(user_points) + 1
        except ValueError:
            return None
    
    def reset_user_points(self, user_id: str, reason: str = "Сброс поинтов"):
        """Сбрасывает поинты пользователя"""
        current_points = self.get_user_points(user_id)
        if current_points > 0:
            self.remove_points(user_id, current_points, reason)
    
    def get_points_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Возвращает таблицу лидеров по поинтам"""
        sorted_users = sorted(
            [(user_id, points) for user_id, points in self.points.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        leaderboard = []
        for rank, (user_id, points) in enumerate(sorted_users[:limit], 1):
            leaderboard.append({
                'rank': rank,
                'user_id': user_id,
                'points': points
            })
        
        return leaderboard
    
    def get_points_for_action(self, action: str) -> int:
        """Возвращает количество поинтов за действие"""
        # Здесь можно добавить логику получения поинтов из конфига
        action_points = {
            'registration': 1,
            'meetup_attendance': 7,
            'feedback_response': 1,
            'presentation': 10,
            'voting': 2
        }
        
        return action_points.get(action, 0)
    
    def award_points_for_action(self, user_id: str, action: str):
        """Начисляет поинты за действие"""
        points = self.get_points_for_action(action)
        if points > 0:
            self.add_points(user_id, points, f"Награда за {action}")

