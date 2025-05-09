import aiosqlite
import asyncio
import datetime
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    async def create_tables(self):
        """Создает необходимые таблицы, если они еще не существуют"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Таблица чатов
                await db.execute(
                    '''
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
                )
                
                # Таблица пользователей
                await db.execute(
                    '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    current_rank TEXT DEFAULT "🔍 Искатель"
                )
            '''
                )
                
                # Проверка наличия колонки current_rank и добавление ее, если отсутствует
                try:
                    # Проверяем PRAGMA для получения информации о столбцах
                    cursor = await db.execute("PRAGMA table_info(users)")
                    columns = await cursor.fetchall()
                    column_names = [column[1] for column in columns]
                    
                    # Если колонки current_rank нет, добавляем ее
                    if 'current_rank' not in column_names:
                        logger.info("Добавление отсутствующей колонки current_rank в таблицу users")
                        await db.execute('''
                            ALTER TABLE users 
                            ADD COLUMN current_rank TEXT DEFAULT "🔍 Искатель"
                        ''')
                        await db.commit()
                except Exception as e:
                    logger.error(f"Ошибка при проверке колонки current_rank: {e}")
                
                # Таблица активности
                await db.execute(
                    '''
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
            '''
                )
                
                # Таблица рангов
                await db.execute(
                    '''
                CREATE TABLE IF NOT EXISTS ranks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    min_points INTEGER,
                    max_points INTEGER
                )
            '''
                )
                
                # Добавляем новую таблицу для отслеживания вопросов дня
                await db.execute(
                    '''
                CREATE TABLE IF NOT EXISTS daily_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    message_id INTEGER,
                    question TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                )
            '''
                )
                
                # Добавляем новую таблицу для отслеживания ответов на вопросы
                await db.execute(
                    '''
                CREATE TABLE IF NOT EXISTS question_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER,
                    user_id INTEGER,
                    points_awarded REAL DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES daily_questions (id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            '''
                )
                
                # Создаем/обновляем ранги
                await db.execute('DELETE FROM ranks')
                # Уровень 1: 0-99 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔍 Искатель', 0, 99))
                # Уровень 2: 100-249 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👣 Путник', 100, 249))
                # Уровень 3: 250-499 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('📚 Ученик', 250, 499))
                # Уровень 4: 500-749 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚔️ Воин чата', 500, 749))
                # Уровень 5: 750-999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧙 Подмастерье', 750, 999))
                # Уровень 6: 1000-1499 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏹 Следопыт', 1000, 1499))
                # Уровень 7: 1500-1999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🛡️ Защитник', 1500, 1999))
                # Уровень 8: 2000-2499 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔮 Мистик', 2000, 2499))
                # Уровень 9: 2500-2999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧠 Мудрец', 2500, 2999))
                # Уровень 10: 3000-3499 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚡ Элементалист', 3000, 3499))
                # Уровень 11: 3500-3999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌙 Ночной клинок', 3500, 3999))
                # Уровень 12: 4000-4499 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌿 Хранитель рощи', 4000, 4499))
                # Уровень 13: 4500-4999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⛏️ Мастер-кузнец', 4500, 4999))
                # Уровень 14: 5000-5999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🐉 Укротитель драконов', 5000, 5999))
                # Уровень 15: 6000-6999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧝 Древний эльф', 6000, 6999))
                # Уровень 16: 7000-7999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌋 Повелитель огня', 7000, 7999))
                # Уровень 17: 8000-8999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('❄️ Хозяин льда', 8000, 8999))
                # Уровень 18: 9000-9999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌪️ Властелин бури', 9000, 9999))
                # Уровень 19: 10000-11999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏰 Командир крепости', 10000, 11999))
                # Уровень 20: 12000-13999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👑 Правитель провинции', 12000, 13999))
                # Уровень 21: 14000-15999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💎 Собиратель артефактов', 14000, 15999))
                # Уровень 22: 16000-19999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌟 Звездный маг', 16000, 19999))
                # Уровень 23: 20000-23999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔱 Морской владыка', 20000, 23999))
                # Уровень 24: 24000-27999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚜️ Королевский рыцарь', 24000, 27999))
                # Уровень 25: 28000-31999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧿 Хранитель тайн', 28000, 31999))
                # Уровень 26: 32000-35999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌓 Повелитель теней', 32000, 35999))
                # Уровень 27: 36000-39999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('☀️ Солнечный чемпион', 36000, 39999))
                # Уровень 28: 40000-44999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🦅 Небесный страж', 40000, 44999))
                # Уровень 29: 45000-49999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🦁 Воин света', 45000, 49999))
                # Уровень 30: 50000-59999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🏆 Легендарный герой', 50000, 59999))
                # Уровень 31: 60000-69999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('👁️ Всевидящий', 60000, 69999))
                # Уровень 32: 70000-79999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💫 Космический странник', 70000, 79999))
                # Уровень 33: 80000-89999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌈 Хранитель миров', 80000, 89999))
                # Уровень 34: 90000-99999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🧚 Бессмертный архимаг', 90000, 99999))
                # Уровень 35: 100000-124999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🔥 Аватар феникса', 100000, 124999))
                # Уровень 36: 125000-149999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌌 Повелитель вселенной', 125000, 149999))
                # Уровень 37: 150000-199999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⭐ Астральный владыка', 150000, 199999))
                # Уровень 38: 200000-249999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌠 Пожиратель звезд', 200000, 249999))
                # Уровень 39: 250000-299999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('⚡ Хранитель вечности', 250000, 299999))
                # Уровень 40: 300000-399999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('💫 Творец реальности', 300000, 399999))
                # Уровень 41: 400000-499999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌞 Солнцеликий', 400000, 499999))
                # Уровень 42: 500000-749999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌑 Лунный оракул', 500000, 749999))
                # Уровень 43: 750000-999999 очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('🌀 Повелитель времени', 750000, 999999))
                # Уровень 44: 1000000+ очков
                await db.execute('INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)', ('✨ Божественная сущность', 1000000, 1000000000))
                
                await db.commit()
                logger.debug("Таблицы и ранги успешно созданы")
                
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
    
    async def add_chat(self, chat_id, title):
        """Добавление нового чата в базу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO chats (chat_id, title) VALUES (?, ?)',
                (chat_id, title)
            )
            await db.commit()
    
    async def add_user(self, user_id, username, first_name, last_name):
        """Добавляет пользователя в базу или обновляет его данные"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Сначала проверяем, существует ли пользователь
                cursor = await db.execute(
                    'SELECT user_id, current_rank FROM users WHERE user_id = ?',
                    (user_id,)
                )
                existing_user = await cursor.fetchone()
                
                if existing_user:
                    # Обновляем данные пользователя
                    await db.execute(
                        'UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?',
                        (username, first_name, last_name, user_id)
                    )
                    # Проверяем, есть ли у пользователя current_rank
                    if len(existing_user) < 2 or existing_user[1] is None:
                        # Добавляем current_rank, если он отсутствует
                        await db.execute(
                            'UPDATE users SET current_rank = ? WHERE user_id = ?',
                            ('🔍 Искатель', user_id)
                        )
                else:
                    # Добавляем нового пользователя
                    await db.execute(
                        'INSERT INTO users (user_id, username, first_name, last_name, current_rank) VALUES (?, ?, ?, ?, ?)',
                        (user_id, username, first_name, last_name, '🔍 Искатель')
                    )
                
                await db.commit()
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
    
    async def add_activity(self, chat_id, user_id, message_type, points):
        """Добавляет запись об активности и проверяет ранг пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Добавляем активность
                await db.execute(
                    'INSERT INTO activity (chat_id, user_id, message_type, points) VALUES (?, ?, ?, ?)',
                    (chat_id, user_id, message_type, points)
                )
                
                # Получаем текущий ранг пользователя
                cursor = await db.execute(
                    'SELECT current_rank FROM users WHERE user_id = ?',
                    (user_id,)
                )
                result = await cursor.fetchone()
                current_rank = result[0] if result and result[0] else "🔍 Искатель"
                
                # Получаем общее количество очков пользователя
                cursor = await db.execute(
                    'SELECT SUM(points) FROM activity WHERE user_id = ?',
                    (user_id,)
                )
                total_points = (await cursor.fetchone())[0] or 0
                
                # Определяем новый ранг на основе общего количества очков
                cursor = await db.execute(
                    'SELECT name FROM ranks WHERE ? BETWEEN min_points AND max_points',
                    (total_points,)
                )
                new_rank_result = await cursor.fetchone()
                new_rank = new_rank_result[0] if new_rank_result else "🔍 Искатель"
                
                # Если ранг изменился, обновляем его в базе
                if current_rank != new_rank:
                    await db.execute(
                        'UPDATE users SET current_rank = ? WHERE user_id = ?',
                        (new_rank, user_id)
                    )
                    await db.commit()
                    
                    # Возвращаем информацию о повышении ранга
                    return {
                        "is_rank_up": True,
                        "old_rank": current_rank,
                        "new_rank": new_rank,
                        "total_points": total_points
                    }
                
                await db.commit()
                return {"is_rank_up": False}
        except Exception as e:
            logger.error(f"Ошибка при добавлении активности: {e}")
            return {"is_rank_up": False}
    
    async def add_game_activity(self, chat_id, user_id, game_type, points):
        """Записывает баллы за игровую активность (emoji_game, quiz)"""
        try:
            # Убедимся что чат и пользователь существуют в базе
            await self.add_chat(chat_id, "Игровая активность")
            await self.add_user(user_id, None, "Игрок", None)
            
            # Записываем активность и проверяем ранг
            rank_info = await self.add_activity(chat_id, user_id, game_type, points)
                
            logger.info(f"Пользователю {user_id} начислено {points} баллов за игру {game_type} в чате {chat_id}")
            return True, rank_info
        except Exception as e:
            logger.error(f"Ошибка при начислении баллов за игру: {e}")
            return False, {"is_rank_up": False}
    
    async def get_user_stats(self, chat_id, user_id):
        """Получение статистики пользователя в конкретном чате"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем общее количество сообщений
            cursor = await db.execute(
                'SELECT COUNT(*) FROM activity WHERE chat_id = ? AND user_id = ?',
                (chat_id, user_id)
            )
            total_messages = (await cursor.fetchone())[0]
            
            # Получаем общее количество очков
            cursor = await db.execute(
                'SELECT SUM(points) FROM activity WHERE chat_id = ? AND user_id = ?',
                (chat_id, user_id)
            )
            total_points = (await cursor.fetchone())[0] or 0
            
            # Получаем текущий ранг
            cursor = await db.execute(
                'SELECT name FROM ranks WHERE ? BETWEEN min_points AND max_points',
                (total_points,)
            )
            rank_result = await cursor.fetchone()
            rank = rank_result[0] if rank_result else "Без ранга"
            
            # Получаем дату последней активности
            cursor = await db.execute(
                'SELECT MAX(timestamp) FROM activity WHERE chat_id = ? AND user_id = ?',
                (chat_id, user_id)
            )
            last_active = (await cursor.fetchone())[0]
            
            # Получаем информацию о следующем ранге
            cursor = await db.execute(
                'SELECT name, min_points FROM ranks WHERE min_points > ? ORDER BY min_points ASC LIMIT 1',
                (total_points,)
            )
            next_rank_result = await cursor.fetchone()
            if next_rank_result:
                next_rank = {
                    "name": next_rank_result[0],
                    "min_points": next_rank_result[1],
                    "points_left": next_rank_result[1] - total_points
                }
            else:
                next_rank = None
            
            return {
                "total_messages": total_messages,
                "total_points": total_points,
                "rank": rank,
                "last_active": last_active,
                "next_rank": next_rank
            }

    async def get_rank_by_points(self, points):
        """Получает ранг по количеству очков"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT name FROM ranks WHERE ? BETWEEN min_points AND max_points',
                (points,)
            )
            rank_result = await cursor.fetchone()
            return rank_result[0] if rank_result else "Без ранга"
    
    async def get_top_users(self, chat_id, limit=10):
        """Получение списка самых активных пользователей в чате"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT u.user_id, u.username, u.first_name, u.last_name, SUM(a.points) as total_points, COUNT(a.id) as total_messages
                FROM activity a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.chat_id = ?
                GROUP BY a.user_id
                ORDER BY total_points DESC
                LIMIT ?
            ''', (chat_id, limit))
            
            return await cursor.fetchall()
    
    async def get_inactive_users(self, chat_id, days=3):
        """Получение списка неактивных пользователей в чате"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем всех пользователей, которые когда-либо писали в этом чате
            cursor = await db.execute('''
                SELECT DISTINCT u.user_id, u.username, u.first_name, u.last_name, MAX(a.timestamp) as last_active
                FROM users u
                JOIN activity a ON u.user_id = a.user_id
                WHERE a.chat_id = ?
                GROUP BY u.user_id
                HAVING last_active < ?
                ORDER BY last_active ASC
            ''', (chat_id, cutoff_str))
            
            return await cursor.fetchall()
    
    async def get_all_chats(self):
        """Получение списка всех чатов, где был активен бот"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT chat_id, title FROM chats
                WHERE chat_id < 0  -- Только групповые чаты (ID < 0)
                ORDER BY joined_date DESC
            ''')
            
            return await cursor.fetchall()
    
    async def get_chat_activity_report(self, chat_id, days=7):
        """Получает отчет об активности чата за указанный период"""
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        async with aiosqlite.connect(self.db_path) as db:
            # Общее количество сообщений за период
            cursor = await db.execute('''
                SELECT COUNT(*) as message_count, 
                       SUM(points) as total_points,
                       COUNT(DISTINCT user_id) as active_users
                FROM activity
                WHERE chat_id = ? AND timestamp > ?
            ''', (chat_id, start_date_str))
            
            activity_summary = await cursor.fetchone()
            
            # Количество сообщений по дням
            cursor = await db.execute('''
                SELECT date(timestamp) as day, COUNT(*) as message_count
                FROM activity
                WHERE chat_id = ? AND timestamp > ?
                GROUP BY day
                ORDER BY day
            ''', (chat_id, start_date_str))
            
            daily_activity = await cursor.fetchall()
            
            return {
                'message_count': activity_summary[0] or 0,
                'total_points': activity_summary[1] or 0,
                'active_users': activity_summary[2] or 0,
                'daily_activity': daily_activity
            }
    
    async def get_most_active_user_today(self, chat_id):
        """Получает самого активного пользователя за последние 24 часа"""
        start_date = datetime.datetime.now() - datetime.timedelta(days=1)
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем пользователя с наибольшим количеством баллов за сегодня
            cursor = await db.execute('''
                SELECT u.user_id, u.username, u.first_name, u.last_name, 
                       COUNT(a.id) as message_count, SUM(a.points) as total_points
                FROM activity a
                JOIN users u ON a.user_id = u.user_id
                WHERE a.chat_id = ? AND a.timestamp > ?
                GROUP BY u.user_id
                ORDER BY total_points DESC
                LIMIT 1
            ''', (chat_id, start_date_str))
            
            result = await cursor.fetchone()
            
            if not result:
                return None
                
            return {
                'user_id': result[0],
                'username': result[1],
                'first_name': result[2],
                'last_name': result[3],
                'message_count': result[4],
                'total_points': result[5]
            }
    
    async def save_question_message_id(self, chat_id, message_id, question):
        """Сохраняет ID сообщения с вопросом дня для отслеживания ответов"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'INSERT INTO daily_questions (chat_id, message_id, question) VALUES (?, ?, ?)',
                    (chat_id, message_id, question)
                )
                await db.commit()
                logger.info(f"Сохранен ID сообщения с вопросом дня: {message_id} в чате {chat_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении ID сообщения с вопросом: {e}")
            return False
    
    async def check_if_response_to_question(self, chat_id, reply_to_message_id):
        """Проверяет, является ли сообщение ответом на вопрос дня"""
        if not reply_to_message_id:
            return None
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Ищем вопрос дня с таким message_id
                cursor = await db.execute(
                    'SELECT id, question FROM daily_questions WHERE chat_id = ? AND message_id = ?',
                    (chat_id, reply_to_message_id)
                )
                result = await cursor.fetchone()
                
                if result:
                    return {
                        'question_id': result[0],
                        'question_text': result[1]
                    }
                return None
        except Exception as e:
            logger.error(f"Ошибка при проверке ответа на вопрос: {e}")
            return None
    
    async def add_question_response(self, question_id, user_id, points=2.0):
        """Добавляет запись об ответе на вопрос дня и начисляет баллы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем, не отвечал ли уже этот пользователь на данный вопрос
                cursor = await db.execute(
                    'SELECT id FROM question_responses WHERE question_id = ? AND user_id = ?',
                    (question_id, user_id)
                )
                existing = await cursor.fetchone()
                
                if existing:
                    # Пользователь уже отвечал на этот вопрос
                    return False, 0
                
                # Добавляем запись об ответе
                await db.execute(
                    'INSERT INTO question_responses (question_id, user_id, points_awarded) VALUES (?, ?, ?)',
                    (question_id, user_id, points)
                )
                
                # Получаем информацию о чате
                cursor = await db.execute(
                    'SELECT chat_id FROM daily_questions WHERE id = ?',
                    (question_id,)
                )
                chat_result = await cursor.fetchone()
                
                if not chat_result:
                    await db.commit()
                    return False, 0
                    
                chat_id = chat_result[0]
                
                # Добавляем активность и баллы пользователю
                rank_info = await self.add_activity(chat_id, user_id, "question_response", points)
                
                await db.commit()
                logger.info(f"Пользователь {user_id} получил {points} баллов за ответ на вопрос дня")
                return True, points
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении ответа на вопрос: {e}")
            return False, 0
    
    async def get_question_stats(self, chat_id, limit=5):
        """Получает статистику по вопросам дня в чате"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Получаем последние вопросы и количество ответов на них
                cursor = await db.execute('''
                    SELECT 
                        q.id, 
                        q.question, 
                        q.timestamp, 
                        COUNT(r.id) as response_count,
                        SUM(r.points_awarded) as total_points
                    FROM daily_questions q
                    LEFT JOIN question_responses r ON q.id = r.question_id
                    WHERE q.chat_id = ?
                    GROUP BY q.id
                    ORDER BY q.timestamp DESC
                    LIMIT ?
                ''', (chat_id, limit))
                
                questions = await cursor.fetchall()
                
                # Собираем результаты
                results = []
                for q in questions:
                    question_id, question_text, timestamp, response_count, total_points = q
                    
                    # Получаем список участников
                    cursor = await db.execute('''
                        SELECT u.user_id, u.first_name, u.last_name, u.username
                        FROM question_responses r
                        JOIN users u ON r.user_id = u.user_id
                        WHERE r.question_id = ?
                        LIMIT 5
                    ''', (question_id,))
                    
                    participants = []
                    async for user_row in cursor:
                        user_id, first_name, last_name, username = user_row
                        name = first_name
                        if last_name:
                            name += f" {last_name}"
                        if username:
                            name += f" (@{username})"
                        participants.append(name)
                    
                    # Сокращаем текст вопроса, если он слишком длинный
                    short_question = question_text
                    if len(short_question) > 40:
                        short_question = short_question[:37] + "..."
                    
                    results.append({
                        'id': question_id,
                        'question': short_question,
                        'full_question': question_text,
                        'timestamp': timestamp,
                        'response_count': response_count or 0,
                        'total_points': total_points or 0,
                        'participants': participants
                    })
                
                return results
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики вопросов: {e}")
            return []

    async def get_last_activity_time(self, chat_id):
        """Получает время последней активности в чате"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    'SELECT MAX(timestamp) FROM activity WHERE chat_id = ?',
                    (chat_id,)
                )
                result = await cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Ошибка при получении времени последней активности: {e}")
            return None
    
    async def get_random_chat_users(self, chat_id, limit=5):
        """Получает случайных пользователей из чата"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Получаем всех пользователей, которые писали в данном чате
                cursor = await db.execute('''
                    SELECT DISTINCT u.user_id, u.username, u.first_name, u.last_name
                    FROM users u
                    JOIN activity a ON u.user_id = a.user_id
                    WHERE a.chat_id = ? AND u.username IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (chat_id, limit))
                
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении случайных пользователей: {e}")
            return []


# Создание экземпляра базы данных
db = Database()

# Инициализация базы данных при запуске
async def init_db():
    await db.create_tables()

if __name__ == "__main__":
    # Если файл запущен напрямую, создаем таблицы
    asyncio.run(init_db()) 