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
        """Создание необходимых таблиц в базе данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица чатов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    title TEXT,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    current_rank TEXT DEFAULT "Искатель"
                )
            ''')
            
            # Таблица сообщений (активности)
            await db.execute('''
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
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ranks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    min_points INTEGER,
                    max_points INTEGER
                )
            ''')
            
            # Удаляем старые ранги (если нужно перегенерировать)
            await db.execute('DELETE FROM ranks')
            
            # Создаем новую тематическую систему рангов, вдохновленную фэнтези/RPG играми
            rank_levels = [
                # Начальные ранги (0-1000 очков)
                ("🔍 Искатель", 0, 99),
                ("👣 Путник", 100, 249),
                ("📚 Ученик", 250, 499),
                ("⚔️ Воин чата", 500, 749),
                ("🧙 Подмастерье", 750, 999),
                
                # Средние ранги (1000-5000 очков)
                ("🏹 Следопыт", 1000, 1499),
                ("🛡️ Защитник", 1500, 1999),
                ("🔮 Мистик", 2000, 2499),
                ("🧠 Мудрец", 2500, 2999),
                ("⚡ Элементалист", 3000, 3499),
                ("🌙 Ночной клинок", 3500, 3999),
                ("🌿 Хранитель рощи", 4000, 4499),
                ("⛏️ Мастер-кузнец", 4500, 4999),
                
                # Продвинутые ранги (5000-20000 очков)
                ("🐉 Укротитель драконов", 5000, 5999),
                ("🧝 Древний эльф", 6000, 6999),
                ("🌋 Повелитель огня", 7000, 7999),
                ("❄️ Хозяин льда", 8000, 8999),
                ("🌪️ Властелин бури", 9000, 9999),
                ("🏰 Командир крепости", 10000, 11999),
                ("👑 Правитель провинции", 12000, 13999),
                ("💎 Собиратель артефактов", 14000, 15999),
                ("🌟 Звездный маг", 16000, 19999),
                
                # Элитные ранги (20000-50000 очков)
                ("🔱 Морской владыка", 20000, 23999),
                ("⚜️ Королевский рыцарь", 24000, 27999),
                ("🧿 Хранитель тайн", 28000, 31999),
                ("🌓 Повелитель теней", 32000, 35999),
                ("☀️ Солнечный чемпион", 36000, 39999),
                ("🦅 Небесный страж", 40000, 44999),
                ("🦁 Воин света", 45000, 49999),
                
                # Легендарные ранги (50000-100000 очков)
                ("🏆 Легендарный герой", 50000, 59999),
                ("👁️ Всевидящий", 60000, 69999),
                ("💫 Космический странник", 70000, 79999),
                ("🌈 Хранитель миров", 80000, 89999),
                ("🧚 Бессмертный архимаг", 90000, 99999),
                
                # Божественные ранги (100000+ очков)
                ("🔥 Аватар феникса", 100000, 124999),
                ("🌌 Повелитель вселенной", 125000, 149999),
                ("⭐ Астральный владыка", 150000, 199999),
                ("🌠 Пожиратель звезд", 200000, 249999),
                ("⚡ Хранитель вечности", 250000, 299999),
                ("💫 Творец реальности", 300000, 399999),
                ("🌞 Солнцеликий", 400000, 499999),
                ("🌑 Лунный оракул", 500000, 749999),
                ("🌀 Повелитель времени", 750000, 999999),
                ("✨ Божественная сущность", 1000000, 1000000000)
            ]
            
            # Вставляем все ранги в базу данных
            for rank_name, min_points, max_points in rank_levels:
                await db.execute(
                    'INSERT INTO ranks (name, min_points, max_points) VALUES (?, ?, ?)',
                    (rank_name, min_points, max_points)
                )
            
            await db.commit()
    
    async def add_chat(self, chat_id, title):
        """Добавление нового чата в базу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO chats (chat_id, title) VALUES (?, ?)',
                (chat_id, title)
            )
            await db.commit()
    
    async def add_user(self, user_id, username, first_name, last_name):
        """Добавление нового пользователя в базу"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                (user_id, username, first_name, last_name)
            )
            await db.commit()
    
    async def add_activity(self, chat_id, user_id, message_type, points):
        """Записывает активность пользователя и проверяет достижение нового ранга"""
        async with aiosqlite.connect(self.db_path) as db:
            # Записываем активность
            await db.execute(
                'INSERT INTO activity (chat_id, user_id, message_type, points) VALUES (?, ?, ?, ?)',
                (chat_id, user_id, message_type, points)
            )
            
            # Проверяем достижение нового ранга
            rank_info = await self.check_rank_up(chat_id, user_id)
            
            await db.commit()
            return rank_info
    
    async def check_rank_up(self, chat_id, user_id):
        """Проверяет, достиг ли пользователь нового ранга"""
        async with aiosqlite.connect(self.db_path) as db:
            # Получаем текущий ранг пользователя
            cursor = await db.execute(
                'SELECT current_rank FROM users WHERE user_id = ?',
                (user_id,)
            )
            result = await cursor.fetchone()
            current_rank = result[0] if result else "🔍 Искатель"
            
            # Получаем общее количество очков
            cursor = await db.execute(
                'SELECT SUM(points) FROM activity WHERE chat_id = ? AND user_id = ?',
                (chat_id, user_id)
            )
            total_points = (await cursor.fetchone())[0] or 0
            
            # Получаем новый ранг на основе общего количества очков
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


# Создание экземпляра базы данных
db = Database()

# Инициализация базы данных при запуске
async def init_db():
    await db.create_tables()

if __name__ == "__main__":
    # Если файл запущен напрямую, создаем таблицы
    asyncio.run(init_db()) 