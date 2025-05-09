import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple

class ScheduleManager:
    def __init__(self, db_path: str):
        """
        Инициализирует менеджер расписания
        
        Args:
            db_path (str): Путь к файлу базы данных
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Инициализирует таблицу для расписания если её нет"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        
        conn.commit()
        conn.close()
    
    def add_event(self, chat_id: int, creator_id: int, title: str, 
                 description: Optional[str], event_time: datetime.datetime) -> int:
        """
        Добавляет новое событие в расписание
        
        Args:
            chat_id (int): ID чата
            creator_id (int): ID создателя события
            title (str): Название события
            description (str, optional): Описание события
            event_time (datetime): Дата и время события
            
        Returns:
            int: ID созданного события
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO schedule_events 
        (chat_id, creator_id, title, description, event_time) 
        VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, creator_id, title, description, event_time))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return event_id
    
    def delete_event(self, event_id: int) -> bool:
        """
        Удаляет событие из расписания
        
        Args:
            event_id (int): ID события
            
        Returns:
            bool: True если событие удалено, False если не найдено
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM schedule_events WHERE id = ?", (event_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        cursor.execute("DELETE FROM schedule_events WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()
        
        return True
    
    def get_event(self, event_id: int) -> Optional[Dict]:
        """
        Возвращает информацию о событии
        
        Args:
            event_id (int): ID события
            
        Returns:
            Dict or None: Информация о событии или None, если не найдено
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, chat_id, creator_id, title, description, 
               event_time, created_at, notification_sent
        FROM schedule_events
        WHERE id = ?
        ''', (event_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        event = dict(row)
        
        # Получаем список участников
        cursor.execute('''
        SELECT user_id, username, joined_at
        FROM event_participants
        WHERE event_id = ?
        ''', (event_id,))
        
        participants = [dict(row) for row in cursor.fetchall()]
        event['participants'] = participants
        
        conn.close()
        
        return event
    
    def get_chat_events(self, chat_id: int, include_past: bool = False) -> List[Dict]:
        """
        Возвращает список событий для чата
        
        Args:
            chat_id (int): ID чата
            include_past (bool): Включать прошедшие события
            
        Returns:
            List[Dict]: Список событий
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
        SELECT id, chat_id, creator_id, title, description, 
               event_time, created_at, notification_sent
        FROM schedule_events
        WHERE chat_id = ?
        '''
        
        if not include_past:
            # Добавляем фильтр по времени, если не нужны прошедшие события
            now = datetime.datetime.now()
            query += " AND event_time > ?"
            cursor.execute(query, (chat_id, now))
        else:
            cursor.execute(query, (chat_id,))
        
        events = [dict(row) for row in cursor.fetchall()]
        
        # Получаем количество участников для каждого события
        for event in events:
            cursor.execute('''
            SELECT COUNT(*) as count
            FROM event_participants
            WHERE event_id = ?
            ''', (event['id'],))
            
            count = cursor.fetchone()['count']
            event['participant_count'] = count
        
        conn.close()
        
        return events
    
    def add_participant(self, event_id: int, user_id: int, username: Optional[str] = None) -> bool:
        """
        Добавляет участника к событию
        
        Args:
            event_id (int): ID события
            user_id (int): ID пользователя
            username (str, optional): Имя пользователя
            
        Returns:
            bool: True если участник добавлен, False если событие не найдено или участник уже добавлен
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Проверяем существует ли событие
            cursor.execute("SELECT id FROM schedule_events WHERE id = ?", (event_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            cursor.execute('''
            INSERT INTO event_participants (event_id, user_id, username)
            VALUES (?, ?, ?)
            ''', (event_id, user_id, username))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Участник уже добавлен
            conn.close()
            return False
    
    def remove_participant(self, event_id: int, user_id: int) -> bool:
        """
        Удаляет участника из события
        
        Args:
            event_id (int): ID события
            user_id (int): ID пользователя
            
        Returns:
            bool: True если участник удален, False если не найден
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        DELETE FROM event_participants
        WHERE event_id = ? AND user_id = ?
        ''', (event_id, user_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_upcoming_events(self, within_hours: int = 24) -> List[Dict]:
        """
        Возвращает список предстоящих событий, для которых еще не отправлены уведомления
        
        Args:
            within_hours (int): Временной интервал в часах
            
        Returns:
            List[Dict]: Список предстоящих событий
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        future = now + datetime.timedelta(hours=within_hours)
        
        cursor.execute('''
        SELECT id, chat_id, creator_id, title, description, event_time
        FROM schedule_events
        WHERE event_time BETWEEN ? AND ?
        AND notification_sent = 0
        ''', (now, future))
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return events
    
    def mark_notification_sent(self, event_id: int) -> None:
        """
        Отмечает, что уведомление о событии отправлено
        
        Args:
            event_id (int): ID события
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE schedule_events
        SET notification_sent = 1
        WHERE id = ?
        ''', (event_id,))
        
        conn.commit()
        conn.close()
    
    def get_participants(self, event_id: int) -> List[Dict]:
        """
        Возвращает список участников события
        
        Args:
            event_id (int): ID события
            
        Returns:
            List[Dict]: Список участников
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT user_id, username, joined_at
        FROM event_participants
        WHERE event_id = ?
        ''', (event_id,))
        
        participants = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return participants 