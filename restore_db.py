import sqlite3
import datetime
import os
import re
import logging
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к базе данных (такой же как в config.py)
DB_PATH = 'activity_bot.db'

def init_db():
    """Инициализирует базу данных, создает необходимые таблицы"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица чатов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        current_rank TEXT DEFAULT "🔍 Искатель"
    )
    ''')
    
    # Таблица активности
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        message_type TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        points REAL DEFAULT 0,
        FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица рангов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ranks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        min_points INTEGER,
        max_points INTEGER
    )
    ''')
    
    # Добавляем новую таблицу для отслеживания вопросов дня
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message_id INTEGER,
        question TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
    )
    ''')
    
    # Добавляем новую таблицу для отслеживания ответов на вопросы
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS question_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        user_id INTEGER,
        points_awarded REAL DEFAULT 0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (question_id) REFERENCES daily_questions (id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Создаем таблицу для хранения событий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schedule_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_time TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notification_sent BOOLEAN DEFAULT 0
    )
    ''')
    
    # Создаем таблицу для хранения участников событий
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES schedule_events (id) ON DELETE CASCADE,
        UNIQUE (event_id, user_id)
    )
    ''')
    
    # Создаем/обновляем ранги
    cursor.execute('DELETE FROM ranks')
    
    # Уровень 1: 0-99 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔍 Искатель', 0, 99))
    # Уровень 2: 100-249 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👣 Путник', 100, 249))
    # Уровень 3: 250-499 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('📚 Ученик', 250, 499))
    # Уровень 4: 500-749 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚔️ Воин чата', 500, 749))
    # Уровень 5: 750-999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧙 Подмастерье', 750, 999))
    # Уровень 6: 1000-1499 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏹 Следопыт', 1000, 1499))
    # Уровень 7: 1500-1999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🛡️ Защитник', 1500, 1999))
    # Уровень 8: 2000-2499 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔮 Мистик', 2000, 2499))
    # Уровень 9: 2500-2999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧠 Мудрец', 2500, 2999))
    # Уровень 10: 3000-3499 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚡ Элементалист', 3000, 3499))
    # Уровень 11: 3500-3999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌙 Ночной клинок', 3500, 3999))
    # Уровень 12: 4000-4499 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌿 Хранитель рощи', 4000, 4499))
    # Уровень 13: 4500-4999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⛏️ Мастер-кузнец', 4500, 4999))
    # Уровень 14: 5000-5999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🐉 Укротитель драконов', 5000, 5999))
    # Уровень 15: 6000-6999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧝 Древний эльф', 6000, 6999))
    # Уровень 16: 7000-7999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌋 Повелитель огня', 7000, 7999))
    # Уровень 17: 8000-8999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('❄️ Хозяин льда', 8000, 8999))
    # Уровень 18: 9000-9999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌪️ Властелин бури', 9000, 9999))
    # Уровень 19: 10000-11999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏰 Командир крепости', 10000, 11999))
    # Уровень 20: 12000-13999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👑 Правитель провинции', 12000, 13999))
    # Уровень 21: 14000-15999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💎 Собиратель артефактов', 14000, 15999))
    # Уровень 22: 16000-19999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌟 Звездный маг', 16000, 19999))
    # Уровень 23: 20000-23999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔱 Морской владыка', 20000, 23999))
    # Уровень 24: 24000-27999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚜️ Королевский рыцарь', 24000, 27999))
    # Уровень 25: 28000-31999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧿 Хранитель тайн', 28000, 31999))
    # Уровень 26: 32000-35999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌓 Повелитель теней', 32000, 35999))
    # Уровень 27: 36000-39999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('☀️ Солнечный чемпион', 36000, 39999))
    # Уровень 28: 40000-44999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🦅 Небесный страж', 40000, 44999))
    # Уровень 29: 45000-49999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🦁 Воин света', 45000, 49999))
    # Уровень 30: 50000-59999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏆 Легендарный герой', 50000, 59999))
    # Уровень 31: 60000-69999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👁️ Всевидящий', 60000, 69999))
    # Уровень 32: 70000-79999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💫 Космический странник', 70000, 79999))
    # Уровень 33: 80000-89999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌈 Хранитель миров', 80000, 89999))
    # Уровень 34: 90000-99999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧚 Бессмертный архимаг', 90000, 99999))
    # Уровень 35: 100000-124999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔥 Аватар феникса', 100000, 124999))
    # Уровень 36: 125000-149999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌌 Повелитель вселенной', 125000, 149999))
    # Уровень 37: 150000-199999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⭐ Астральный владыка', 150000, 199999))
    # Уровень 38: 200000-249999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌠 Пожиратель звезд', 200000, 249999))
    # Уровень 39: 250000-299999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚡ Хранитель вечности', 250000, 299999))
    # Уровень 40: 300000-399999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💫 Творец реальности', 300000, 399999))
    # Уровень 41: 400000-499999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌞 Солнцеликий', 400000, 499999))
    # Уровень 42: 500000-749999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌑 Лунный оракул', 500000, 749999))
    # Уровень 43: 750000-999999 очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌀 Повелитель времени', 750000, 999999))
    # Уровень 44: 1000000+ очков
    cursor.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('✨ Божественная сущность', 1000000, 1000000000))
    
    conn.commit()
    conn.close()
    
    logger.info("База данных инициализирована успешно")

def add_chat(chat_id, title):
    """Добавляет чат в базу данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR IGNORE INTO chats (chat_id, title) VALUES (?, ?)',
        (chat_id, title)
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Чат {title} (ID: {chat_id}) добавлен в базу данных")

def add_user(user_id, username, first_name, current_rank):
    """Добавляет пользователя в базу данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR REPLACE INTO users (user_id, username, first_name, current_rank) VALUES (?, ?, ?, ?)',
        (user_id, username, first_name, current_rank)
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Пользователь {first_name} (@{username}) добавлен в базу данных")

def add_activity(chat_id, user_id, points, message_count):
    """Добавляет активность пользователя в базу данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Вычисляем среднее количество баллов за одно сообщение
    avg_points_per_message = points / message_count
    
    # Распределяем даты активности за последние 30 дней
    now = datetime.datetime.now()
    
    # Добавляем активность
    for i in range(message_count):
        # Распределяем сообщения по датам (последние 30 дней)
        days_ago = int((i / message_count) * 30)
        message_date = now - datetime.timedelta(days=days_ago, 
                                               hours=random.randint(0, 23), 
                                               minutes=random.randint(0, 59))
        
        # Определяем тип сообщения (для разнообразия)
        message_types = ['text', 'long_text', 'media', 'reply']
        message_type = message_types[i % len(message_types)]
        
        # Назначаем баллы в зависимости от типа сообщения
        if message_type == 'text':
            msg_points = 1.0
        elif message_type == 'long_text':
            msg_points = 1.5
        elif message_type == 'media':
            msg_points = 1.7
        elif message_type == 'reply':
            msg_points = 2.0
        
        # Небольшая случайность в баллах
        msg_points *= random.uniform(0.9, 1.1)
        
        # Записываем активность
        cursor.execute(
            'INSERT INTO activity (chat_id, user_id, message_type, timestamp, points) VALUES (?, ?, ?, ?, ?)',
            (chat_id, user_id, message_type, message_date, msg_points)
        )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Добавлено {message_count} записей активности для пользователя {user_id}")

def parse_top_users_data(data):
    """Парсит данные топ пользователей из текста"""
    users = []
    
    # Регулярное выражение для извлечения информации о пользователях
    pattern = r"(\d+)\.\s+(.*?)\s+\(@(.*?)\)\s+⭐\s+([\d.]+)\s+баллов\s+\|\s+💬\s+(\d+)\s+сообщений\s+🏆\s+Ранг:\s+(.*?)$"
    
    # Специальная обработка для медальных мест
    medal_pattern = r"🥇|🥈|🥉"
    
    lines = data.strip().split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Пропускаем заголовок
        if "Топ 10 активных участников" in line:
            i += 1
            continue
        
        # Проверяем, есть ли в строке информация о пользователе
        if "@" in line:
            # Обрабатываем медальное место
            if re.search(medal_pattern, line):
                # Для медальных мест информация разделена на 3 строки
                if i + 2 < len(lines):
                    name_line = line
                    points_line = lines[i + 1].strip()
                    rank_line = lines[i + 2].strip()
                    
                    # Извлекаем имя и username
                    name_match = re.search(r"(🥇|🥈|🥉)\s+(.*?)\s+\(@(.*?)\)", name_line)
                    if name_match:
                        position = "1" if "🥇" in name_match.group(1) else ("2" if "🥈" in name_match.group(1) else "3")
                        name = name_match.group(2)
                        username = name_match.group(3)
                        
                        # Извлекаем баллы и сообщения
                        points_match = re.search(r"⭐\s+([\d.]+)\s+баллов\s+\|\s+💬\s+(\d+)\s+сообщений", points_line)
                        if points_match:
                            points = float(points_match.group(1))
                            messages = int(points_match.group(2))
                            
                            # Извлекаем ранг
                            rank_match = re.search(r"🏆\s+Ранг:\s+(.*?)$", rank_line)
                            if rank_match:
                                rank = rank_match.group(1)
                                
                                users.append({
                                    "position": int(position),
                                    "name": name,
                                    "username": username,
                                    "points": points,
                                    "messages": messages,
                                    "rank": rank
                                })
                    
                    i += 3  # Переходим к следующему пользователю
                    continue
            
            # Обрабатываем обычные места (без медалей)
            match = re.search(pattern, line)
            if match:
                position = int(match.group(1))
                name = match.group(2)
                username = match.group(3)
                points = float(match.group(4))
                messages = int(match.group(5))
                rank = match.group(6)
                
                users.append({
                    "position": position,
                    "name": name,
                    "username": username,
                    "points": points,
                    "messages": messages,
                    "rank": rank
                })
        
        i += 1
    
    return users

def restore_database(top_users_data, chat_id=-123456789, chat_title="Восстановленный чат"):
    """Восстанавливает базу данных с топ пользователями"""
    # Проверяем, существует ли уже файл базы данных
    if os.path.exists(DB_PATH):
        backup_path = f"{DB_PATH}.backup.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.rename(DB_PATH, backup_path)
        logger.info(f"Существующая база данных сохранена как {backup_path}")
    
    # Инициализируем базу данных
    init_db()
    
    # Добавляем чат
    add_chat(chat_id, chat_title)
    
    # Парсим данные пользователей
    users = parse_top_users_data(top_users_data)
    
    # Временный искусственный ID
    user_id_start = 10000
    
    # Добавляем пользователей и их активность
    for user in users:
        # Используем позицию пользователя для создания уникального ID
        user_id = user_id_start + user["position"]
        
        # Добавляем пользователя
        add_user(user_id, user["username"], user["name"], user["rank"])
        
        # Добавляем активность пользователя
        add_activity(chat_id, user_id, user["points"], user["messages"])
    
    logger.info(f"Восстановление базы данных завершено. Добавлено {len(users)} пользователей.")
    return users

if __name__ == "__main__":
    # Текст с топ пользователями
    top_users_text = """
🏆 Топ 10 активных участников чата:

🥇 ｆｒａｍｅｚ ＸＤ. 🌺 (@kishimoro)
   ⭐ 13978.5 баллов | 💬 9430 сообщений
   🏆 Ранг: 👑 Правитель провинции

🥈 darklight (@negritos23)
   ⭐ 6579.0 баллов | 💬 4280 сообщений
   🏆 Ранг: 🧝 Древний эльф

🥉 ᑕᕼᗩᑎ 🎲XD 🌺 (@rhytesx)
   ⭐ 5659.0 баллов | 💬 2814 сообщений
   🏆 Ранг: 🐉 Укротитель драконов

4. гуль🌺 (@Kggghoul)
   ⭐ 5174.5 баллов | 💬 3413 сообщений
   🏆 Ранг: 🐉 Укротитель драконов

5. anesthesia (@sspitinmyfacee)
   ⭐ 2372.5 баллов | 💬 1458 сообщений
   🏆 Ранг: 🔮 Мистик

6. ァ☠𝖌𝖍𝖔𝖚𝖑☠ァ fearful sad (@Demorkg)
   ⭐ 1965.0 баллов | 💬 1236 сообщений
   🏆 Ранг: 🛡️ Защитник

7. Вася крутой 228 (@Fgkjffn)
   ⭐ 1685.0 баллов | 💬 968 сообщений
   🏆 Ранг: 🛡️ Защитник

8. ꒷﹫ ;𝓢.ʟ ˓˓⌗𝐃e͟𝘮 .. (@GeniusDem)
   ⭐ 1546.0 баллов | 💬 1096 сообщений
   🏆 Ранг: 🛡️ Защитник

9. grrrulz (@grrrulz)
   ⭐ 714.0 баллов | 💬 504 сообщений
   🏆 Ранг: ⚔️ Воин чата

10. 𝖇𝖔𝖘𝖙𝖎𝖐 #bizex (@Da1tedenegplz0)
   ⭐ 709.5 баллов | 💬 462 сообщений
   🏆 Ранг: ⚔️ Воин чата
    """
    
    # ID вашего чата (замените на реальный ID)
    your_chat_id = -1001847369650
    
    # Название вашего чата (замените на реальное название)
    your_chat_title = "Vibe chat XD"
    
    # Восстанавливаем базу данных
    users = restore_database(top_users_text, your_chat_id, your_chat_title)
    
    print(f"База данных успешно восстановлена!")
    print(f"Восстановлено {len(users)} пользователей")
    print(f"База данных: {DB_PATH}")
    print("\nДля запуска бота с восстановленной базой данных выполните команду:")
    print("python main.py") 