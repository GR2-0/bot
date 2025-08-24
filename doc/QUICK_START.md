# 🚀 Быстрый старт на новом ПК

## 📋 Чек-лист для продолжения работы

### 1. Подготовка окружения
- [ ] Скопировать папку проекта `gr2_bot/`
- [ ] Установить Python 3.8+
- [ ] Создать виртуальное окружение: `python3 -m venv venv`
- [ ] Активировать: `source venv/bin/activate` (Linux/Mac) или `venv\Scripts\activate` (Windows)
- [ ] Установить зависимости: `pip install -r requirements.txt`

### 2. Настройка конфигурации
- [ ] Отредактировать `data/private/config/bot_config.json`
  - Вставить токен бота
  - Указать ID группы коммьюнити
  - Указать ID админской группы
- [ ] Проверить `data/private/config/points_config.json`

### 3. Первый запуск
- [ ] Запустить: `python main.py`
- [ ] Проверить логи в `bot.log`
- [ ] Отправить боту `/start` в Telegram

### 4. Проверка работоспособности
- [ ] Бот отвечает на команды
- [ ] Нет ошибок импорта модулей
- [ ] Создаются файлы данных в `data/private/`

## 🔧 Основные команды для тестирования

```bash
# Проверка структуры
ls -la
tree data/ src/

# Проверка Python
python --version
python -c "import src.config; print('Config OK')"

# Запуск бота
python main.py
```

## 📁 Ключевые файлы для проверки

- `src/bot.py` - основной модуль бота
- `src/config.py` - конфигурация
- `src/models/` - модели данных
- `data/private/config/` - настройки
- `requirements.txt` - зависимости

## ⚠️ Частые проблемы

1. **ImportError** - проверьте активацию venv
2. **FileNotFoundError** - создайте папки data/private/
3. **TelegramError** - проверьте токен и права бота
4. **PermissionError** - проверьте права на папки

## 📚 Документация

- `README.md` - полная документация проекта
- `INSTALL.md` - подробная инструкция по установке
- `PROJECT_CONTEXT.md` - контекст разработки

---
*Готово к продолжению работы! 🎯*
