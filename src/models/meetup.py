"""
Модуль для управления митапами
"""
import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional


class MeetupManager:
    """Класс для управления митапами"""
    
    def __init__(self, meetups_file: str = "data/private/meetups/meetups.json"):
        self.meetups_file = Path(meetups_file)
        self.meetups = {}
        self.load_meetups()
    
    def load_meetups(self):
        """Загружает митапы из файла"""
        try:
            if self.meetups_file.exists():
                with open(self.meetups_file, 'r', encoding='utf-8') as f:
                    self.meetups = json.load(f)
            else:
                # Создаём директорию если её нет
                self.meetups_file.parent.mkdir(parents=True, exist_ok=True)
                self.meetups = {}
                self.save_meetups()
        except Exception as e:
            print(f"Ошибка загрузки митапов: {e}")
            self.meetups = {}
    
    def save_meetups(self):
        """Сохраняет митапы в файл"""
        try:
            with open(self.meetups_file, 'w', encoding='utf-8') as f:
                json.dump(self.meetups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения митапов: {e}")
    
    def create_meetup(self, meetup_data: Dict) -> str:
        """Создаёт новый митап"""
        meetup_id = str(uuid.uuid4())
        
        # Добавляем недостающие поля
        meetup_data.setdefault('id', meetup_id)
        meetup_data.setdefault('status', 'planned')
        meetup_data.setdefault('attendees', [])
        meetup_data.setdefault('presentations', [])
        meetup_data.setdefault('created_at', datetime.now().isoformat())
        
        self.meetups[meetup_id] = meetup_data
        self.save_meetups()
        
        return meetup_id
    
    def get_meetup(self, meetup_id: str) -> Optional[Dict]:
        """Возвращает данные митапа"""
        return self.meetups.get(meetup_id)
    
    def update_meetup(self, meetup_id: str, updates: Dict):
        """Обновляет данные митапа"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        # Проверяем, можно ли редактировать митап
        meetup = self.meetups[meetup_id]
        if meetup.get('status') in ['completed', 'archived']:
            raise ValueError("Завершённые митапы нельзя редактировать")
        
        self.meetups[meetup_id].update(updates)
        self.meetups[meetup_id]['updated_at'] = datetime.now().isoformat()
        self.save_meetups()
    
    def delete_meetup(self, meetup_id: str):
        """Удаляет митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        # Проверяем, можно ли удалить митап
        meetup = self.meetups[meetup_id]
        if meetup.get('status') in ['completed', 'archived']:
            raise ValueError("Завершённые митапы нельзя удалять")
        
        del self.meetups[meetup_id]
        self.save_meetups()
    
    def start_meetup(self, meetup_id: str):
        """Запускает митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        self.meetups[meetup_id]['status'] = 'active'
        self.meetups[meetup_id]['started_at'] = datetime.now().isoformat()
        self.save_meetups()
    
    def end_meetup(self, meetup_id: str):
        """Завершает митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        self.meetups[meetup_id]['status'] = 'completed'
        self.meetups[meetup_id]['ended_at'] = datetime.now().isoformat()
        self.save_meetups()
    
    def archive_meetup(self, meetup_id: str):
        """Архивирует митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        self.meetups[meetup_id]['status'] = 'archived'
        self.meetups[meetup_id]['archived_at'] = datetime.now().isoformat()
        self.save_meetups()
    
    def add_attendee(self, meetup_id: str, user_id: str):
        """Добавляет участника на митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        # Проверяем, не зарегистрирован ли уже пользователь
        attendees = self.meetups[meetup_id].get('attendees', [])
        if any(att['user_id'] == user_id for att in attendees):
            raise ValueError("Пользователь уже зарегистрирован на этот митап")
        
        # Добавляем участника
        attendee = {
            'user_id': user_id,
            'registration_time': datetime.now().strftime('%H:%M:%S'),
            'registration_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        self.meetups[meetup_id]['attendees'].append(attendee)
        self.save_meetups()
    
    def remove_attendee(self, meetup_id: str, user_id: str):
        """Убирает участника с митапа"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        attendees = self.meetups[meetup_id].get('attendees', [])
        self.meetups[meetup_id]['attendees'] = [
            att for att in attendees if att['user_id'] != user_id
        ]
        self.save_meetups()
    
    def add_presentation(self, meetup_id: str, presentation_data: Dict):
        """Добавляет доклад к митапу"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")
        
        presentation = {
            'id': str(uuid.uuid4()),
            'title': presentation_data['title'],
            'speaker': presentation_data['speaker'],
            'added_at': datetime.now().isoformat()
        }
        
        self.meetups[meetup_id]['presentations'].append(presentation)
        self.save_meetups()
    
    def get_editable_meetups(self) -> List[Dict]:
        """Возвращает митапы, которые можно редактировать"""
        return [
            meetup for meetup in self.meetups.values()
            if meetup.get('status') in ['planned', 'active']
        ]
    
    def get_deletable_meetups(self) -> List[Dict]:
        """Возвращает митапы, которые можно удалить"""
        return [
            meetup for meetup in self.meetups.values()
            if meetup.get('status') in ['planned', 'active']
        ]
    
    def get_active_meetups(self) -> List[Dict]:
        """Возвращает активные митапы"""
        return [
            meetup for meetup in self.meetups.values()
            if meetup.get('status') == 'active'
        ]
    
    def get_meetups_by_date(self, target_date: str) -> List[Dict]:
        """Возвращает митапы по дате"""
        return [
            meetup for meetup in self.meetups.values()
            if meetup.get('date') == target_date
        ]
    
    def get_total_meetups(self) -> int:
        """Возвращает общее количество митапов"""
        return len(self.meetups)
    
    def get_active_meetups_count(self) -> int:
        """Возвращает количество активных митапов"""
        return len(self.get_active_meetups())
    
    def get_meetup_stats(self, meetup_id: str) -> Dict:
        """Возвращает статистику митапа"""
        meetup = self.get_meetup(meetup_id)
        if not meetup:
            return {}
        
        attendees = meetup.get('attendees', [])
        presentations = meetup.get('presentations', [])
        
        return {
            'id': meetup_id,
            'name': meetup.get('name'),
            'date': meetup.get('date'),
            'status': meetup.get('status'),
            'total_attendees': len(attendees),
            'total_presentations': len(presentations),
            'start_time': meetup.get('start_time'),
            'end_time': meetup.get('end_time'),
            'location': meetup.get('location')
        }
    
    def get_all_meetups_stats(self) -> List[Dict]:
        """Возвращает статистику всех митапов"""
        return [self.get_meetup_stats(meetup_id) for meetup_id in self.meetups.keys()]

