import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла (если файл существует)
load_dotenv()

# Настройки бота
BOT_TOKEN = "7831139892:AAHTc8jrKW9LzNVKLivxaxhliBzin4m9Ybw"
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")

# Список ID администраторов (может быть пустым)
ADMIN_IDS = [1323242332]  # User ID гуль🌺 (Kggghoul)
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_IDS.extend([int(admin_id) for admin_id in admin_ids_str.split(",") if admin_id])

# Настройки базы данных
DB_PATH = "activity_bot.db"

# Настройки геймификации
POINTS_PER_MESSAGE = 1  # Очки за одно сообщение
POINTS_PER_REACTION = 0.5  # Очки за одну реакцию
POINTS_PER_REPLY = 2  # Очки за ответ на сообщение

# Настройки напоминаний
INACTIVITY_THRESHOLD_DAYS = 1  # Кол-во дней неактивности для напоминания (для тестирования) 