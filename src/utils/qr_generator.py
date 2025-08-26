"""
Модуль для генерации QR-кодов
"""
import qrcode
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import io


class QRCodeGenerator:
    """Класс для генерации и управления QR-кодами"""

    def __init__(self, qr_dir: str = "data/private/qr_codes"):
        self.qr_dir = Path(qr_dir)
        self.qr_dir.mkdir(parents=True, exist_ok=True)
        self.active_codes = {}  # meetup_id -> {code: data, expires_at: timestamp}

    def generate_qr_code(self, meetup_id: str, deep_link: str) -> str:
        """
        Генерирует QR-код для диплинка

        Args:
            meetup_id: ID митапа
            deep_link: Диплинк для регистрации

        Returns:
            Путь к сгенерированному QR-коду
        """
        try:
            # Создаём уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qr_{meetup_id}_{timestamp}.png"
            filepath = self.qr_dir / filename

            # Генерируем QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(deep_link)
            qr.make(fit=True)

            # Создаём изображение
            img = qr.make_image(fill_color="black", back_color="white")

            # Сохраняем файл
            img.save(filepath)

            return str(filepath)

        except Exception as e:
            print(f"Ошибка генерации QR-кода: {e}")
            return ""

    def create_deep_link(self, meetup_id: str, user_id: str = None) -> str:
        """
        Создаёт диплинк для регистрации на митап

        Args:
            meetup_id: ID митапа
            user_id: ID пользователя (опционально)

        Returns:
            Диплинк для регистрации
        """
        from config import config
        bot_username = config.get_bot_username()
        base_url = f"https://t.me/{bot_username}"

        if user_id:
            # Персональная ссылка для конкретного пользователя
            return f"{base_url}?start=meetup_{meetup_id}_{user_id}"
        else:
            # Общая ссылка для митапа
            return f"{base_url}?start=meetup_{meetup_id}"

    def generate_meetup_qr_codes(self, meetup_id: str, interval_seconds: int = 10) -> List[Dict]:
        """
        Генерирует серию QR-кодов для митапа

        Args:
            meetup_id: ID митапа
            interval_seconds: Интервал между генерацией кодов в секундах

        Returns:
            Список сгенерированных QR-кодов
        """
        codes = []
        current_time = datetime.now()

        # Генерируем код каждые interval_seconds секунд
        for i in range(0, 3600, interval_seconds):  # Генерируем на час
            timestamp = current_time + timedelta(seconds=i)
            deep_link = self.create_deep_link(meetup_id)

            code_data = {
                'id': str(uuid.uuid4()),
                'meetup_id': meetup_id,
                'deep_link': deep_link,
                'generated_at': timestamp.isoformat(),
                'expires_at': (timestamp + timedelta(seconds=interval_seconds)).isoformat(),
                'is_used': False,
                'used_by': None,
                'used_at': None
            }

            codes.append(code_data)

        # Сохраняем активные коды
        self.active_codes[meetup_id] = codes

        return codes

    def mark_code_as_used(self, meetup_id: str, code_id: str, user_id: str):
        """
        Отмечает QR-код как использованный

        Args:
            meetup_id: ID митапа
            code_id: ID QR-кода
            user_id: ID пользователя, который использовал код
        """
        if meetup_id in self.active_codes:
            for code in self.active_codes[meetup_id]:
                if code['id'] == code_id:
                    code['is_used'] = True
                    code['used_by'] = user_id
                    code['used_at'] = datetime.now().isoformat()
                    break

    def get_valid_code(self, meetup_id: str) -> Optional[Dict]:
        """
        Возвращает валидный (неиспользованный и неистекший) QR-код для митапа

        Args:
            meetup_id: ID митапа

        Returns:
            Валидный QR-код или None
        """
        if meetup_id not in self.active_codes:
            return None

        current_time = datetime.now()

        for code in self.active_codes[meetup_id]:
            expires_at = datetime.fromisoformat(code['expires_at'])

            if not code['is_used'] and current_time < expires_at:
                return code

        return None

    def cleanup_expired_codes(self):
        """Удаляет истекшие QR-коды"""
        current_time = datetime.now()

        for meetup_id, codes in self.active_codes.items():
            # Фильтруем только валидные коды
            valid_codes = []

            for code in codes:
                expires_at = datetime.fromisoformat(code['expires_at'])

                if current_time < expires_at:
                    valid_codes.append(code)
                else:
                    # Удаляем файл QR-кода если он существует
                    self._delete_qr_file(code)

            self.active_codes[meetup_id] = valid_codes

    def _delete_qr_file(self, code: Dict):
        """Удаляет файл QR-кода"""
        try:
            # Здесь можно добавить логику удаления файлов
            # Пока просто очищаем данные
            pass
        except Exception as e:
            print(f"Ошибка удаления файла QR-кода: {e}")

    def get_meetup_qr_stats(self, meetup_id: str) -> Dict:
        """
        Возвращает статистику QR-кодов для митапа

        Args:
            meetup_id: ID митапа

        Returns:
            Статистика QR-кодов
        """
        if meetup_id not in self.active_codes:
            return {
                'total_codes': 0,
                'used_codes': 0,
                'valid_codes': 0,
                'expired_codes': 0
            }

        codes = self.active_codes[meetup_id]
        current_time = datetime.now()

        used_codes = sum(1 for code in codes if code['is_used'])
        expired_codes = sum(1 for code in codes
                            if datetime.fromisoformat(code['expires_at']) < current_time)
        valid_codes = len(codes) - used_codes - expired_codes

        return {
            'total_codes': len(codes),
            'used_codes': used_codes,
            'valid_codes': valid_codes,
            'expired_codes': expired_codes
        }

    def stop_meetup_qr_generation(self, meetup_id: str):
        """Останавливает генерацию QR-кодов для митапа"""
        if meetup_id in self.active_codes:
            del self.active_codes[meetup_id]
