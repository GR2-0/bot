"""
Модуль для управления митапами
"""
import json
import uuid
from datetime import datetime, date, time, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class MeetupManager:
    """Класс для управления митапами"""

    def __init__(self, meetups_file: str =
                 "data/private/meetups/meetups.json"):
        self.meetups_file = Path(meetups_file)
        self.meetups = {}
        self.moscow_tz = timezone(timedelta(hours=3))  # UTC+3 для Москвы
        self.load_meetups()

    def get_moscow_time(self) -> datetime:
        """Возвращает текущее время в московском часовом поясе"""
        return datetime.now(self.moscow_tz)

    def get_moscow_date(self) -> str:
        """Возвращает текущую дату в московском часовом поясе в формате YYYY-MM-DD"""
        return self.get_moscow_time().strftime('%Y-%m-%d')

    def get_moscow_datetime(self) -> str:
        """Возвращает текущее время в московском часовом поясе в ISO формате"""
        return self.get_moscow_time().isoformat()

    def convert_to_moscow_time(self, dt: datetime) -> datetime:
        """Конвертирует время в московский часовой пояс"""
        if dt.tzinfo is None:
            # Если время без часового пояса, считаем что это UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self.moscow_tz)

    def parse_moscow_time(self, time_str: str) -> time:
        """Парсит время в московском часовом поясе"""
        try:
            # Парсим время как локальное московское время
            time_obj = datetime.strptime(time_str, '%H:%M').time()
            # Создаем datetime с московским часовым поясом
            moscow_dt = datetime.combine(date.today(), time_obj,
                                         tzinfo=self.moscow_tz)
            return moscow_dt.time()
        except ValueError:
            raise ValueError("Неверный формат времени. Используйте HH:MM")

    def parse_moscow_date(self, date_str: str) -> str:
        """Парсит дату в московском часовом поясе"""
        try:
            # Парсим дату как локальную московскую дату
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            return date_str
        except ValueError:
            raise ValueError("Неверный формат даты. Используйте YYYY-MM-DD")

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
        meetup_data.setdefault('created_at', self.get_moscow_datetime())

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
        self.meetups[meetup_id]['updated_at'] = self.get_moscow_datetime()
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
        self.meetups[meetup_id]['started_at'] = self.get_moscow_datetime()
        self.save_meetups()

    def end_meetup(self, meetup_id: str):
        """Завершает митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")

        self.meetups[meetup_id]['status'] = 'completed'
        self.meetups[meetup_id]['ended_at'] = self.get_moscow_datetime()
        self.save_meetups()

    def archive_meetup(self, meetup_id: str):
        """Архивирует митап"""
        if meetup_id not in self.meetups:
            raise ValueError(f"Митап {meetup_id} не найден")

        self.meetups[meetup_id]['status'] = 'archived'
        self.meetups[meetup_id]['archived_at'] = self.get_moscow_datetime()
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
            'registration_time': self.get_moscow_time().strftime('%H:%M:%S'),
            'registration_date': self.get_moscow_date()
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
            'added_at': self.get_moscow_datetime()
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

    def create_meetup_interactive(self, meetup_data: Dict) -> Dict:
        """
        Создаёт митап с интерактивным вводом данных

        Args:
            meetup_data: Словарь с данными митапа

        Returns:
            Словарь с результатом создания
        """
        try:
            # Валидация обязательных полей
            required_fields = ['name', 'date', 'start_time',
                               'end_time', 'location', 'capacity']
            for field in required_fields:
                if field not in meetup_data:
                    return {
                        'success': False,
                        'error': f'Отсутствует обязательное поле: {field}'
                    }

            # Валидация даты
            try:
                datetime.strptime(meetup_data['date'], '%Y-%m-%d')
            except ValueError:
                return {
                    'success': False,
                    'error': 'Неверный формат даты. Используйте YYYY-MM-DD'
                }

            # Валидация времени
            try:
                datetime.strptime(meetup_data['start_time'], '%H:%M')
                datetime.strptime(meetup_data['end_time'], '%H:%M')
            except ValueError:
                return {
                    'success': False,
                    'error': 'Неверный формат времени. Используйте HH:MM'
                }

            # Валидация вместимости
            if not isinstance(meetup_data['capacity'], int) or meetup_data['capacity'] <= 0:
                return {
                    'success': False,
                    'error': 'Вместимость должна быть положительным числом'
                }

            # Создаём митап
            meetup_id = self.create_meetup(meetup_data)

            return {
                'success': True,
                'meetup_id': meetup_id,
                'meetup_data': meetup_data
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка создания митапа: {str(e)}'
            }

    def validate_meetup_data(self, meetup_data: Dict) -> Dict:
        """
        Валидирует данные митапа

        Args:
            meetup_data: Словарь с данными митапа

        Returns:
            Словарь с результатом валидации
        """
        errors = []

        # Проверка названия
        if not meetup_data.get('name') or len(meetup_data['name'].strip()) < 2:
            errors.append('Название митапа должно содержать минимум 2 символа')

        # Проверка даты и времени
        if meetup_data.get('date') and meetup_data.get('start_time'):
            try:
                meetup_date = datetime.strptime(
                    meetup_data['date'], '%Y-%m-%d').date()
                start_time = datetime.strptime(
                    meetup_data['start_time'], '%H:%M').time()

                # Создаем datetime для митапа в московском времени
                meetup_datetime = datetime.combine(meetup_date, start_time,
                                                   tzinfo=self.moscow_tz)
                moscow_now = self.get_moscow_time()

                # Проверяем, что митап начинается в будущем
                if meetup_datetime <= moscow_now:
                    errors.append('Митап должен начинаться в будущем времени')

            except ValueError as e:
                if 'date' in str(e):
                    errors.append(
                        'Неверный формат даты. Используйте YYYY-MM-DD')
                elif 'time' in str(e):
                    errors.append('Неверный формат времени. Используйте HH:MM')
                else:
                    errors.append(f'Ошибка валидации даты/времени: {e}')

        # Проверка времени
        if meetup_data.get('start_time') and meetup_data.get('end_time'):
            try:
                start_time = datetime.strptime(
                    meetup_data['start_time'], '%H:%M').time()
                end_time = datetime.strptime(
                    meetup_data['end_time'], '%H:%M').time()
                if start_time >= end_time:
                    errors.append(
                        'Время начала должно быть раньше времени окончания')
            except ValueError:
                errors.append('Неверный формат времени. Используйте HH:MM')

        # Проверка места
        if not meetup_data.get('location') or len(meetup_data['location'].strip()) < 3:
            errors.append(
                'Место проведения должно содержать минимум 3 символа')

        # Проверка вместимости
        if meetup_data.get('capacity'):
            try:
                capacity = int(meetup_data['capacity'])
                if capacity <= 0:
                    errors.append(
                        'Вместимость должна быть положительным числом')
                elif capacity > 1000:
                    errors.append(
                        'Вместимость не может превышать 1000 человек')
            except (ValueError, TypeError):
                errors.append('Вместимость должна быть числом')

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def update_meetup_statuses(self):
        """Автоматически обновляет статусы митапов на основе текущего времени"""
        moscow_now = self.get_moscow_time()
        updated = False

        for meetup_id, meetup in self.meetups.items():
            if meetup.get('status') == 'planned':
                # Проверяем, не пора ли запустить митап
                try:
                    meetup_date = datetime.strptime(
                        meetup['date'], '%Y-%m-%d').date()
                    start_time = datetime.strptime(
                        meetup['start_time'], '%H:%M').time()
                    meetup_start = datetime.combine(meetup_date, start_time,
                                                    tzinfo=self.moscow_tz)

                    if meetup_start <= moscow_now:
                        meetup['status'] = 'active'
                        meetup['started_at'] = self.get_moscow_datetime()
                        updated = True
                        print(f"Митап {meetup['name']} автоматически запущен")
                except (ValueError, KeyError):
                    continue

            elif meetup.get('status') == 'active':
                # Проверяем, не пора ли завершить митап
                try:
                    meetup_date = datetime.strptime(
                        meetup['date'], '%Y-%m-%d').date()
                    end_time = datetime.strptime(
                        meetup['end_time'], '%H:%M').time()
                    meetup_end = datetime.combine(meetup_date, end_time,
                                                  tzinfo=self.moscow_tz)

                    if meetup_end <= moscow_now:
                        meetup['status'] = 'completed'
                        meetup['ended_at'] = self.get_moscow_datetime()
                        updated = True
                        print(f"Митап {meetup['name']} автоматически завершен")
                except (ValueError, KeyError):
                    continue

        if updated:
            self.save_meetups()

        return updated
