import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла (если файл существует)
load_dotenv()

# Токен бота из переменных окружения или напрямую
TOKEN = '7712430479:AAEV4jORCqdZKbkuwdaDmB2ReisgPnLemgU'
BOT_TOKEN = TOKEN  # Для обратной совместимости

# Имя пользователя бота (без @)
BOT_USERNAME = os.getenv('BOT_USERNAME', 'your_bot_username')

# Список ID администраторов (может быть пустым)
ADMIN_ID = [
    1323242332,  # Основной администратор
    123456789,   # Пример ID администратора
    987654321    # Можно добавить несколько ID
]
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_ID.extend([int(admin_id) for admin_id in admin_ids_str.split(",") if admin_id])

# Для обратной совместимости - оба имени переменных должны работать
ADMIN_IDS = ADMIN_ID  # Важно: это ссылка на тот же список, а не копия

# Настройки базы данных
DB_PATH = os.getenv('DB_PATH', 'activity_bot.db')

# Настройки системы активности
POINTS_PER_MESSAGE = 1.0  # Базовое количество баллов за сообщение
POINTS_PER_REPLY = 1.5    # Баллы за ответ на сообщение
MEDIA_BONUS = 0.7         # Бонус за отправку медиа
LONG_MESSAGE_BONUS = 0.5  # Бонус за длинное сообщение (>100 символов)

# Настройки игр
EMOJI_GAME_POINTS = 5.0   # Баллы за правильный ответ в игре эмодзи
QUIZ_GAME_POINTS = 3.0    # Баллы за правильный ответ в викторине

# Настройки периодических задач
INACTIVE_USER_DAYS = 7    # Количество дней для определения неактивного пользователя
REPORT_INTERVAL_DAYS = 7  # Интервал между отчетами об активности в днях
DAILY_TOPIC_HOUR = 10     # Час для отправки ежедневной темы (по UTC)
ACTIVE_USER_HOUR = 20     # Час для объявления самого активного пользователя (по UTC)

# Настройки челленджей
CHALLENGE_DURATION_DAYS = 3  # Продолжительность одного челленджа в днях
CHALLENGE_POINTS = 10.0      # Баллы за выполнение челленджа

# Ограничения на частоту игр (в секундах)
GAME_COOLDOWN = 300  # 5 минут между играми в одном чате

# Настройки напоминаний
INACTIVITY_THRESHOLD_DAYS = 1  # Кол-во дней неактивности для напоминания (для тестирования) 
