import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.markdown import bold, text
import logging
import traceback
import datetime  # Добавляем импорт для работы с датами и временем
import asyncio

from database import db  # Импортируем базу данных для начисления баллов

logger = logging.getLogger(__name__)

# Константы для баллов за игры
EMOJI_GAME_POINTS = 5
QUIZ_GAME_POINTS = 3

# Система отслеживания активных игр
class GameTracker:
    def __init__(self):
        self.active_game = None  # Тип активной игры: "emoji" или "quiz"
        self.game_chat_id = None  # ID чата, где идёт игра
        self.game_starter_id = None  # ID пользователя, который начал игру
        self.game_start_time = None  # Время начала игры
        
        # Система отслеживания времени последнего запуска игр пользователями
        self.user_last_game = {}  # словарь {user_id: {'timestamp': datetime, 'game_type': str}}
        # Время ограничения в минутах между запусками игр одним пользователем
        self.cooldown_minutes = 60

    def is_game_active(self):
        """Проверяет, активна ли в данный момент какая-либо игра"""
        return self.active_game is not None

    def start_game(self, game_type, chat_id, user_id):
        """Регистрирует начало новой игры"""
        # Устанавливаем данные активной игры
        self.active_game = game_type
        self.game_chat_id = chat_id
        self.game_starter_id = user_id
        self.game_start_time = datetime.datetime.now()
        
        # Записываем время последнего запуска игры пользователем
        self.user_last_game[user_id] = {
            'timestamp': self.game_start_time,
            'game_type': game_type
        }
        
        logger.info(f"Запущена игра {game_type} в чате {chat_id} пользователем {user_id}")

    def end_game(self):
        """Завершает текущую игру"""
        if self.active_game:
            logger.info(f"Завершена игра {self.active_game} в чате {self.game_chat_id}")
            self.active_game = None
            self.game_chat_id = None
            self.game_starter_id = None
            self.game_start_time = None

    def get_game_info(self):
        """Возвращает информацию о текущей активной игре"""
        if not self.is_game_active():
            return "Нет активных игр"
        
        game_duration = datetime.datetime.now() - self.game_start_time
        minutes = int(game_duration.total_seconds() // 60)
        seconds = int(game_duration.total_seconds() % 60)
        
        game_name = "Угадай по эмодзи" if self.active_game == "emoji" else "Викторина"
        
        return f"Сейчас идёт игра: {game_name}\nЗапустил: ID {self.game_starter_id}\nВремя: {minutes} мин. {seconds} сек."
    
    def can_user_start_game(self, user_id):
        """Проверяет, может ли пользователь запустить игру (прошло ли достаточно времени)"""
        if user_id not in self.user_last_game:
            return True, None
            
        last_game = self.user_last_game[user_id]
        now = datetime.datetime.now()
        time_passed = now - last_game['timestamp']
        
        # Рассчитываем, сколько времени осталось до возможности запуска
        cooldown_seconds = self.cooldown_minutes * 60
        seconds_passed = time_passed.total_seconds()
        seconds_left = cooldown_seconds - seconds_passed
        
        if seconds_left <= 0:
            return True, None
            
        # Если время не прошло, форматируем оставшееся время
        minutes_left = int(seconds_left // 60)
        seconds_left = int(seconds_left % 60)
        
        game_type = "Угадай по эмодзи" if last_game['game_type'] == "emoji" else "Викторина"
        
        return False, {
            'minutes': minutes_left,
            'seconds': seconds_left,
            'game_type': game_type,
            'timestamp': last_game['timestamp'].strftime('%H:%M:%S')
        }


# Создаём экземпляр трекера игр
game_tracker = GameTracker()

# Класс для хранения состояний игр
class GameStates(StatesGroup):
    emoji_game = State()  # Состояние для игры "Угадай по эмодзи"
    quiz_game = State()   # Состояние для викторины


# Игра "Угадай по эмодзи"
class EmojiGame:
    def __init__(self):
        # Словарь с эмодзи-загадками
        self.emoji_riddles = {
            "🧙‍♂️📓⚡🔮": "Гарри Поттер",
            "🦁👑🌍": "Король Лев",
            "👸❄️⛄": "Холодное сердце",
            "👠🧚‍♀️🎃": "Золушка",
            "🚢❄️💑": "Титаник",
            "🕷️🕸️👨": "Человек-паук",
            "🤖👽💥": "Трансформеры",
            "🦖🏝️🚙": "Парк Юрского периода",
            "🧸👦🍯": "Винни-Пух",
            "👻👻🔫": "Охотники за привидениями",
            # Новые фильмы
            "👨‍👩‍👧📦🏠": "Вверх",
            "🧠😢😡😄": "Головоломка",
            "🤵🔫🕴️": "Джеймс Бонд",
            "🔍🧩🕵️": "Шерлок Холмс",
            "👑💍🧙‍♂️": "Властелин колец",
            "🤖❤️🌎": "ВАЛЛ-И",
            "🦇🃏🌃": "Бэтмен",
            "🦕🦖🌋": "Мир Юрского периода",
            "🧜‍♀️🐠🌊": "Русалочка",
            "🔴⚔️👽": "Звездные войны",
            # Игры
            "🍄👨🐢": "Марио",
            "⛏️🌳🧱": "Minecraft",
            "🔫🎮🎖️": "Call of Duty",
            "🚗🏎️💨": "Need for Speed",
            "🏆⚽🎮": "FIFA",
            "🧙‍♂️🐲👑": "Skyrim",
            "🧟🔫🏙️": "Resident Evil",
            "🗡️🛡️🐉": "Dark Souls",
            "🤖🦾🤯": "Cyberpunk 2077",
            "🏝️🏴‍☠️⚓": "Assassin's Creed: Black Flag",
            # Мультфильмы и сериалы
            "🟡👨‍👩‍👧‍👦🍩": "Симпсоны",
            "👨‍🔬👦🔬": "Рик и Морти",
            "🏰🐉👑": "Игра престолов",
            "🧪👨‍🔬💊": "Во все тяжкие",
            "👽👧🚲": "Очень странные дела",
            "🤠🌵🐴": "Ковбой Бибоп",
            "👑👸🏹": "Мерида",
            "👨‍👩‍👧‍👦🏠👻": "Дом совы",
            "🐼🥋🐯": "Кунг-фу Панда",
            "🔥🌪️💧": "Аватар: Легенда об Аанге"
        }
        self.current_riddle = None
        self.current_answer = None
        
    def get_random_riddle(self):
        """Получить случайную эмодзи-загадку"""
        try:
            riddles_list = list(self.emoji_riddles.items())
            if not riddles_list:
                logger.error("Список загадок пуст!")
                return "❓", "Ошибка"
            
            selected = random.choice(riddles_list)
            self.current_riddle, self.current_answer = selected
            logger.debug(f"Выбрана загадка: {self.current_riddle} -> {self.current_answer}")
            return self.current_riddle
        except Exception as e:
            logger.exception(f"Ошибка при выборе загадки: {e}")
            self.current_riddle = "❓"
            self.current_answer = "Ошибка"
            return self.current_riddle
    
    def check_answer(self, user_answer):
        """Проверить ответ пользователя"""
        if not self.current_answer:
            return False
        
        # Приводим ответы к нижнему регистру для сравнения
        return user_answer.lower() == self.current_answer.lower()


# Викторина
class QuizGame:
    def __init__(self):
        # Вопросы для викторины
        self.questions = [
            {
                "question": "Какая страна является самой большой по площади?",
                "options": ["Китай", "США", "Россия", "Канада"],
                "correct": 2  # Россия (индекс 2)
            },
            {
                "question": "Сколько планет в Солнечной системе?",
                "options": ["7", "8", "9", "10"],
                "correct": 1  # 8 (индекс 1)
            },
            {
                "question": "Кто написал 'Войну и мир'?",
                "options": ["Достоевский", "Толстой", "Чехов", "Пушкин"],
                "correct": 1  # Толстой (индекс 1)
            },
            {
                "question": "Какой элемент имеет символ 'O' в периодической таблице?",
                "options": ["Олово", "Осмий", "Кислород", "Золото"],
                "correct": 2  # Кислород (индекс 2)
            },
            {
                "question": "Столица Японии?",
                "options": ["Киото", "Осака", "Токио", "Сеул"],
                "correct": 2  # Токио (индекс 2)
            },
            # Новые вопросы по истории
            {
                "question": "В каком году началась Вторая мировая война?",
                "options": ["1937", "1939", "1941", "1945"],
                "correct": 1  # 1939 (индекс 1)
            },
            {
                "question": "Кто был первым президентом США?",
                "options": ["Томас Джефферсон", "Джордж Вашингтон", "Авраам Линкольн", "Джон Адамс"],
                "correct": 1  # Джордж Вашингтон (индекс 1)
            },
            # Вопросы по географии
            {
                "question": "Какая река самая длинная в мире?",
                "options": ["Амазонка", "Нил", "Янцзы", "Миссисипи"],
                "correct": 0  # Амазонка (индекс 0)
            },
            {
                "question": "В какой стране находится Тадж-Махал?",
                "options": ["Индия", "Пакистан", "Иран", "ОАЭ"],
                "correct": 0  # Индия (индекс 0)
            },
            # Вопросы по науке
            {
                "question": "Какой газ наиболее распространен в атмосфере Земли?",
                "options": ["Кислород", "Углекислый газ", "Азот", "Аргон"],
                "correct": 2  # Азот (индекс 2)
            },
            {
                "question": "Какое животное самое быстрое на суше?",
                "options": ["Лев", "Гепард", "Антилопа", "Тигр"],
                "correct": 1  # Гепард (индекс 1)
            },
            # Вопросы по искусству
            {
                "question": "Кто написал картину 'Звездная ночь'?",
                "options": ["Клод Моне", "Пабло Пикассо", "Винсент Ван Гог", "Сальвадор Дали"],
                "correct": 2  # Ван Гог (индекс 2)
            },
            {
                "question": "Какой музыкальный инструмент имеет 88 клавиш?",
                "options": ["Орган", "Фортепиано", "Аккордеон", "Синтезатор"],
                "correct": 1  # Фортепиано (индекс 1)
            },
            # Вопросы по спорту
            {
                "question": "В каком городе прошли первые современные Олимпийские игры?",
                "options": ["Париж", "Афины", "Лондон", "Рим"],
                "correct": 1  # Афины (индекс 1)
            },
            {
                "question": "Сколько игроков в команде по футболу?",
                "options": ["10", "11", "12", "9"],
                "correct": 1  # 11 (индекс 1)
            },
            # Вопросы по технологиям
            {
                "question": "Кто основал компанию Microsoft?",
                "options": ["Стив Джобс", "Билл Гейтс", "Марк Цукерберг", "Илон Маск"],
                "correct": 1  # Билл Гейтс (индекс 1)
            },
            {
                "question": "В каком году был запущен первый iPhone?",
                "options": ["2005", "2007", "2009", "2010"],
                "correct": 1  # 2007 (индекс 1)
            },
            # Вопросы по кино
            {
                "question": "Какой фильм получил Оскар за лучший фильм в 2020 году?",
                "options": ["1917", "Джокер", "Паразиты", "Однажды в Голливуде"],
                "correct": 2  # Паразиты (индекс 2)
            },
            {
                "question": "Кто сыграл Железного человека в киновселенной Marvel?",
                "options": ["Крис Эванс", "Роберт Дауни-младший", "Крис Хемсворт", "Марк Руффало"],
                "correct": 1  # Роберт Дауни-младший (индекс 1)
            },
            # Вопросы по еде
            {
                "question": "Какая страна является родиной пиццы?",
                "options": ["Франция", "Испания", "Греция", "Италия"],
                "correct": 3  # Италия (индекс 3)
            },
            {
                "question": "Из чего делают традиционный васаби?",
                "options": ["Из горчицы", "Из хрена", "Из зеленого перца", "Из имбиря"],
                "correct": 1  # Из хрена (индекс 1)
            }
        ]
        self.current_question = None
        
    def get_random_question(self):
        """Получить случайный вопрос"""
        self.current_question = random.choice(self.questions)
        return self.current_question
    
    def check_answer(self, option_index):
        """Проверить ответ пользователя по индексу варианта"""
        if not self.current_question:
            return False
        
        return option_index == self.current_question["correct"]
    
    def get_formatted_question(self):
        """Получить отформатированный текст вопроса с вариантами ответов"""
        if not self.current_question:
            return "Ошибка: вопрос не выбран"
        
        question_text = bold(self.current_question["question"]) + "\n\n"
        
        for i, option in enumerate(self.current_question["options"]):
            question_text += f"{i+1}. {option}\n"
            
        return question_text


# Создание экземпляров игр
emoji_game = EmojiGame()
quiz_game = QuizGame()


# Функция для безопасного получения состояния в групповых чатах
async def get_current_state(state: FSMContext):
    """Безопасно получает текущее состояние FSM в групповых чатах"""
    try:
        return await state.get_state()
    except Exception as e:
        logger.debug(f"Ошибка при получении состояния: {str(e)}")
        return None

# Безопасное завершение состояния с обработкой ошибок
async def safe_finish_state(state: FSMContext):
    """Безопасно завершает состояние FSM с обработкой возможных ошибок в групповых чатах"""
    try:
        # Сначала сбрасываем данные состояния
        await state.update_data({})
        # Затем завершаем состояние
        await state.finish()
        logger.debug("Состояние успешно завершено")
    except Exception as e:
        logger.debug(f"Ошибка при завершении состояния: {str(e)}")
        try:
            # Альтернативный метод сброса состояния
            current_state = await get_current_state(state)
            if current_state:
                await state.reset_state(with_data=False)
                await state.reset_data()
                logger.debug("Состояние сброшено альтернативным методом")
        except Exception as e2:
            logger.error(f"Критическая ошибка при сбросе состояния: {str(e2)}")
    
    # Независимо от результата, сбрасываем текущие значения игр
    try:
        # Сбрасываем текущие значения игр для предотвращения багов при следующем запуске
        emoji_game.current_riddle = None
        emoji_game.current_answer = None
        quiz_game.current_question = None
        # Завершаем игру в трекере
        game_tracker.end_game()
    except Exception as e:
        logger.error(f"Ошибка при сбросе игровых данных: {str(e)}")


# Обработчик команды /emoji_game
async def cmd_emoji_game(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Запущена команда emoji_game пользователем {user_id} в чате {chat_id}")
        
        # Проверяем, не активна ли уже какая-то игра
        if game_tracker.is_game_active():
            game_info = game_tracker.get_game_info()
            await message.answer(
                f"❌ В данный момент уже идёт игра!\n\n{game_info}\n\nПожалуйста, дождитесь завершения текущей игры.",
                parse_mode=types.ParseMode.MARKDOWN
            )
            return
        
        # Проверяем, прошло ли достаточно времени с момента последней игры пользователя
        can_start, cooldown_info = game_tracker.can_user_start_game(user_id)
        if not can_start:
            await message.answer(
                f"⏳ Вы запускали игру слишком часто!\n\n"
                f"Последняя игра: {cooldown_info['game_type']} в {cooldown_info['timestamp']}\n"
                f"Вы сможете запустить новую игру через {cooldown_info['minutes']} мин. {cooldown_info['seconds']} сек.",
                parse_mode=types.ParseMode.MARKDOWN
            )
            return
        
        # Сначала проверяем, есть ли уже активное состояние
        current_state = await get_current_state(state)
        if current_state:
            logger.warning(f"Пользователь {user_id} уже находится в состоянии {current_state}, сбрасываем")
            await safe_finish_state(state)
        
        # Получаем загадку и проверяем, что она корректна
        riddle = emoji_game.get_random_riddle()
        if not riddle or not emoji_game.current_answer:
            logger.error("Не удалось получить корректную загадку")
            await message.answer("Произошла ошибка при генерации загадки. Попробуйте еще раз позже.")
            return
            
        logger.debug(f"Загадка получена: {riddle}")
        
        # Регистрируем игру в трекере
        game_tracker.start_game("emoji", chat_id, user_id)
        
        # Формируем сообщение
        response_text = (
            f"🎮 *Игра 'Угадай по эмодзи'*\n\n"
            f"Угадайте фильм, игру или персонажа по эмодзи:\n\n"
            f"{riddle}\n\n"
            f"Напишите ваш ответ в чат. У вас есть 3 попытки!"
        )
        
        # Отправляем сообщение
        await message.answer(response_text, parse_mode=types.ParseMode.MARKDOWN)
        logger.debug(f"Сообщение отправлено пользователю {user_id}")
        
        # Устанавливаем состояние и данные
        await state.update_data(attempts=0, riddle=riddle, answer=emoji_game.current_answer)
        await GameStates.emoji_game.set()
        logger.info(f"Состояние GameStates.emoji_game установлено для пользователя {user_id}")
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике emoji_game: {e}\n{error_traceback}")
        await message.answer(f"Произошла ошибка при запуске игры. Попробуйте позже.")
        await safe_finish_state(state)


# Обработчик ответов в игре Emoji
async def process_emoji_answer(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Получен ответ от пользователя {user_id} в состоянии emoji_game: {message.text}")
        
        user_answer = message.text
        user_data = await state.get_data()
        attempts = user_data.get('attempts', 0)
        
        # Проверка, что загадка была корректно установлена
        if not emoji_game.current_riddle or not emoji_game.current_answer:
            logger.error(f"Текущая загадка не найдена, перезапускаем игру")
            await message.answer("Произошла ошибка с текущей загадкой. Начните игру заново командой /emoji_game")
            await safe_finish_state(state)
            return
        
        # Проверка ответа
        if user_answer.lower() == emoji_game.current_answer.lower():
            # Правильный ответ
            points = max(5.0 - attempts * 0.5, 1.0)  # Меньше баллов за больше попыток
            success, rank_info = await db.add_game_activity(chat_id, user_id, 'emoji_game', points)
            
            # Базовое сообщение об успехе
            response = (
                f"🎯 Правильный ответ, {message.from_user.full_name}!\n\n"
                f"Загадка: {emoji_game.current_riddle}\n"
                f"Ответ: {emoji_game.current_answer}\n"
                f"Попыток использовано: {attempts + 1}\n"
                f"Получено баллов: {points}"
            )
            
            await message.answer(response)
            
            # Если произошло повышение ранга, отправляем поздравление
            if success and rank_info and rank_info.get('is_rank_up'):
                old_rank = rank_info.get('old_rank')
                new_rank = rank_info.get('new_rank')
                total_points = rank_info.get('total_points')
                
                congrats_text = (
                    f"🎖 *Повышение ранга!* 🎖\n\n"
                    f"👤 {message.from_user.full_name}\n"
                    f"📊 Набрано {total_points:.1f} баллов\n"
                    f"📈 Прошлый ранг: {old_rank}\n"
                    f"✨ Новый ранг: {new_rank}\n\n"
                    f"🎉 Поздравляем с достижением!"
                )
                
                await message.answer(congrats_text, parse_mode="Markdown")
            
            # Сбрасываем состояние и загадку
            emoji_game.current_riddle = None
            emoji_game.current_answer = None
            await safe_finish_state(state)
            
            # С некоторой вероятностью запускаем новую игру
            if random.random() < 0.3:  # 30% вероятность
                await asyncio.sleep(2)  # Пауза перед следующей загадкой
                await message.answer("💡 Давайте сыграем еще раз!")
                await cmd_emoji_game(message, state)
        else:
            # Неправильный ответ
            attempts += 1
            
            # Обновляем количество попыток
            await state.update_data(attempts=attempts)
            
            # Разные ответы в зависимости от количества попыток
            if attempts < 3:
                await message.answer(f"❌ Неправильно! Попробуйте еще раз. Попытка {attempts}/3")
            else:
                # Если исчерпаны все попытки, показываем ответ
                await message.answer(
                    f"⛔ Попытки закончились!\n\n"
                    f"Загадка: {emoji_game.current_riddle}\n"
                    f"Правильный ответ: {emoji_game.current_answer}"
                )
                
                # Начисляем утешительный балл за участие
                success, rank_info = await db.add_game_activity(chat_id, user_id, 'emoji_game', 0.5)
                
                # Если произошло повышение ранга, отправляем поздравление
                if success and rank_info and rank_info.get('is_rank_up'):
                    old_rank = rank_info.get('old_rank')
                    new_rank = rank_info.get('new_rank')
                    total_points = rank_info.get('total_points')
                    
                    congrats_text = (
                        f"🎖 *Повышение ранга!* 🎖\n\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"📊 Набрано {total_points:.1f} баллов\n"
                        f"📈 Прошлый ранг: {old_rank}\n"
                        f"✨ Новый ранг: {new_rank}\n\n"
                        f"🎉 Поздравляем с достижением!"
                    )
                    
                    await message.answer(congrats_text, parse_mode="Markdown")
                
                # Сбрасываем состояние и загадку
                emoji_game.current_riddle = None
                emoji_game.current_answer = None
                await safe_finish_state(state)
                
                # С некоторой вероятностью запускаем новую игру
                if random.random() < 0.3:  # 30% вероятность
                    await asyncio.sleep(2)
                    await message.answer("💡 Давайте сыграем еще раз!")
                    await cmd_emoji_game(message, state)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа в Emoji-игре: {e}")
        await message.answer("Произошла ошибка при обработке ответа. Пожалуйста, начните игру заново.")
        await safe_finish_state(state)


# Обработчик команды /quiz
async def cmd_quiz(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Запущена команда quiz пользователем {user_id} в чате {chat_id}")
        
        # Проверяем, не активна ли уже какая-то игра
        if game_tracker.is_game_active():
            game_info = game_tracker.get_game_info()
            await message.answer(
                f"❌ В данный момент уже идёт игра!\n\n{game_info}\n\nПожалуйста, дождитесь завершения текущей игры.",
                parse_mode=types.ParseMode.MARKDOWN
            )
            return
        
        # Проверяем, прошло ли достаточно времени с момента последней игры пользователя
        can_start, cooldown_info = game_tracker.can_user_start_game(user_id)
        if not can_start:
            await message.answer(
                f"⏳ Вы запускали игру слишком часто!\n\n"
                f"Последняя игра: {cooldown_info['game_type']} в {cooldown_info['timestamp']}\n"
                f"Вы сможете запустить новую игру через {cooldown_info['minutes']} мин. {cooldown_info['seconds']} сек.",
                parse_mode=types.ParseMode.MARKDOWN
            )
            return
        
        # Сбрасываем текущее состояние, если оно есть
        current_state = await get_current_state(state)
        if current_state:
            logger.warning(f"Пользователь уже находится в состоянии {current_state}, сбрасываем")
            await safe_finish_state(state)
            
        # Получаем вопрос викторины и проверяем его корректность
        question = quiz_game.get_random_question()
        if not question:
            logger.error("Не удалось получить корректный вопрос")
            await message.answer("Произошла ошибка при генерации вопроса. Попробуйте еще раз позже.")
            return
        
        # Регистрируем игру в трекере
        game_tracker.start_game("quiz", chat_id, user_id)
            
        formatted_question = quiz_game.get_formatted_question()
        
        # Сохраняем данные вопроса в состоянии для восстановления при необходимости
        # Важно: сохраняем правильный ответ в виде текста для последующей проверки
        correct_index = question["correct"]
        correct_answer = question["options"][correct_index]
        
        await state.update_data(
            question=question["question"],
            options=question["options"],
            correct=question["correct"],
            correct_answer=correct_answer,
            attempts=0
        )
        
        await message.answer(
            f"🎮 *Викторина*\n\n{formatted_question}\n"
            f"Ответьте цифрой от 1 до {len(question['options'])}",
            parse_mode=types.ParseMode.MARKDOWN
        )
        
        await GameStates.quiz_game.set()
        logger.info(f"Состояние GameStates.quiz_game установлено для пользователя {user_id}")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике quiz: {e}\n{error_traceback}")
        await message.answer(f"Произошла ошибка при запуске викторины. Попробуйте позже.")
        await safe_finish_state(state)


# Обработчик ответов в викторине
async def process_quiz_answer(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Получен ответ от пользователя {user_id} в состоянии quiz: {message.text}")
        
        user_answer = message.text.strip()
        user_data = await state.get_data()
        question = user_data.get('question')
        options = user_data.get('options', [])
        correct = user_data.get('correct')
        correct_answer = user_data.get('correct_answer')
        attempts = user_data.get('attempts', 0)
        
        # Проверка что данные вопроса корректно установлены
        if not question or not correct_answer or correct is None or not options:
            logger.error(f"Данные вопроса некорректны, перезапускаем викторину")
            await message.answer("Произошла ошибка с текущим вопросом. Начните викторину заново командой /quiz")
            await safe_finish_state(state)
            return
        
        # Проверяем, является ли ответ числом от 1 до len(options)
        is_valid_option = False
        option_index = -1
        
        try:
            # Проверяем, ввел ли пользователь число
            if user_answer.isdigit():
                option_index = int(user_answer) - 1  # Преобразуем в 0-индексированный
                if 0 <= option_index < len(options):
                    is_valid_option = True
            
            # Если ответ не число, проверяем, может быть пользователь ввел текст ответа
            if not is_valid_option:
                # Проверяем, не ввел ли пользователь сам ответ текстом
                for i, option in enumerate(options):
                    if user_answer.lower() == option.lower():
                        option_index = i
                        is_valid_option = True
                        break
        except:
            is_valid_option = False
        
        # Если ответ не является корректным вариантом
        if not is_valid_option:
            await message.answer(f"❗ Пожалуйста, ответьте цифрой от 1 до {len(options)} или введите текст варианта ответа.")
            return
        
        # Проверка правильности ответа
        if option_index == correct:
            # Правильный ответ
            points = max(3.0 - attempts * 0.5, 1.0)  # Меньше баллов за больше попыток
            success, rank_info = await db.add_game_activity(chat_id, user_id, 'quiz', points)
            
            response = (
                f"✅ Правильный ответ, {message.from_user.full_name}!\n\n"
                f"Вопрос: {question}\n"
                f"Ответ: {correct_answer}\n"
                f"Попыток использовано: {attempts + 1}\n"
                f"Получено баллов: {points}"
            )
            
            await message.answer(response)
            
            # Если произошло повышение ранга, отправляем поздравление
            if success and rank_info and rank_info.get('is_rank_up'):
                old_rank = rank_info.get('old_rank')
                new_rank = rank_info.get('new_rank')
                total_points = rank_info.get('total_points')
                
                congrats_text = (
                    f"🎖 *Повышение ранга!* 🎖\n\n"
                    f"👤 {message.from_user.full_name}\n"
                    f"📊 Набрано {total_points:.1f} баллов\n"
                    f"📈 Прошлый ранг: {old_rank}\n"
                    f"✨ Новый ранг: {new_rank}\n\n"
                    f"🎉 Поздравляем с достижением!"
                )
                
                await message.answer(congrats_text, parse_mode="Markdown")
            
            # Завершаем состояние
            await safe_finish_state(state)
            
            # С некоторой вероятностью запускаем новую викторину
            if random.random() < 0.3:  # 30% вероятность
                await asyncio.sleep(2)
                await message.answer("🧠 Давайте сыграем еще раз!")
                await cmd_quiz(message, state)
        else:
            # Неправильный ответ
            attempts += 1
            
            # Обновляем количество попыток
            await state.update_data(attempts=attempts)
            
            # Получаем текст выбранного (неправильного) варианта
            chosen_option = options[option_index]
            
            # Разные ответы в зависимости от количества попыток
            if attempts < 3:
                await message.answer(f"❌ Неправильно! Вы выбрали: {chosen_option}\nПопробуйте еще раз. Попытка {attempts}/3")
            else:
                # Если исчерпаны все попытки, показываем ответ
                await message.answer(
                    f"⛔ Попытки закончились!\n\n"
                    f"Вопрос: {question}\n"
                    f"Вы выбрали: {chosen_option}\n"
                    f"Правильный ответ: {correct_answer}"
                )
                
                # Начисляем утешительный балл за участие
                success, rank_info = await db.add_game_activity(chat_id, user_id, 'quiz', 0.5)
                
                # Если произошло повышение ранга, отправляем поздравление
                if success and rank_info and rank_info.get('is_rank_up'):
                    old_rank = rank_info.get('old_rank')
                    new_rank = rank_info.get('new_rank')
                    total_points = rank_info.get('total_points')
                    
                    congrats_text = (
                        f"🎖 *Повышение ранга!* 🎖\n\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"📊 Набрано {total_points:.1f} баллов\n"
                        f"📈 Прошлый ранг: {old_rank}\n"
                        f"✨ Новый ранг: {new_rank}\n\n"
                        f"🎉 Поздравляем с достижением!"
                    )
                    
                    await message.answer(congrats_text, parse_mode="Markdown")
                
                # Завершаем состояние
                await safe_finish_state(state)
                
                # С некоторой вероятностью запускаем новую викторину
                if random.random() < 0.3:  # 30% вероятность
                    await asyncio.sleep(2)
                    await message.answer("🧠 Давайте сыграем еще раз!")
                    await cmd_quiz(message, state)
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при обработке ответа в викторине: {e}\n{error_traceback}")
        await message.answer("Произошла ошибка при обработке ответа. Пожалуйста, начните викторину заново.")
        await safe_finish_state(state)


# Обработчик команды для изменения времени ограничения (только для админов)
async def cmd_set_cooldown(message: types.Message):
    try:
        from config import ADMIN_IDS
        
        user_id = message.from_user.id
        
        # Проверка, является ли пользователь администратором
        if user_id not in ADMIN_IDS and user_id != message.chat.owner_id:
            await message.answer("❌ Эта команда доступна только администраторам.")
            return
            
        # Разбор аргументов команды
        command_args = message.get_args()
        if not command_args:
            await message.answer(
                f"⚙️ Текущее ограничение: {game_tracker.cooldown_minutes} минут\n\n"
                f"Для изменения используйте формат: /set_cooldown [минуты]"
            )
            return
            
        try:
            minutes = int(command_args)
            if minutes < 1:
                await message.answer("❌ Ограничение не может быть меньше 1 минуты.")
                return
                
            old_cooldown = game_tracker.cooldown_minutes
            game_tracker.cooldown_minutes = minutes
            
            await message.answer(
                f"✅ Ограничение успешно изменено!\n\n"
                f"Старое значение: {old_cooldown} минут\n"
                f"Новое значение: {minutes} минут\n\n"
                f"Теперь пользователи смогут запускать игры не чаще одного раза в {minutes} минут."
            )
            logger.info(f"Администратор {user_id} изменил время ограничения с {old_cooldown} на {minutes} минут")
            
        except ValueError:
            await message.answer("❌ Пожалуйста, укажите корректное числовое значение в минутах.")
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при изменении времени ограничения: {e}\n{error_traceback}")
        await message.answer("Произошла ошибка при изменении времени ограничения.")


# Регистрация обработчиков игровых команд
def register_game_handlers(dp):
    """
    ВАЖНО: Эта функция больше не используется.
    Регистрация игровых обработчиков происходит напрямую в main.py 
    для предотвращения циклических зависимостей.
    Функция оставлена для документации и обратной совместимости
    """
    logger.info("Функция register_game_handlers устарела. Обработчики регистрируются напрямую в main.py")
    # ВНИМАНИЕ: Код ниже не выполняется, так как эта функция больше не используется
    # Оставлен для документации и обратной совместимости
    try:
        # Регистрируем игровые команды ПЕРЕД обработчиками состояний
        dp.register_message_handler(cmd_emoji_game, commands=["emoji_game"])
        dp.register_message_handler(cmd_quiz, commands=["quiz"])
        
        # Добавляем обработчик команды для завершения активной игры (только для админов)
        dp.register_message_handler(cmd_end_game, commands=["end_game"])
        
        # Добавляем обработчик команды для изменения времени ограничения
        dp.register_message_handler(cmd_set_cooldown, commands=["set_cooldown"])
        
        # Регистрируем обработчики состояний
        dp.register_message_handler(process_emoji_answer, state=GameStates.emoji_game)
        dp.register_message_handler(process_quiz_answer, state=GameStates.quiz_game)
        
        logger.info("Игровые обработчики успешно зарегистрированы")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при регистрации игровых обработчиков: {e}\n{error_traceback}")


# Обработчик команды /end_game для завершения активной игры (доступен всем для тестирования)
async def cmd_end_game(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Проверяем, есть ли активная игра
        if not game_tracker.is_game_active():
            await message.answer("В данный момент нет активных игр.")
            return
            
        # Получаем информацию о текущей игре
        game_info = game_tracker.get_game_info()
        
        # Завершаем игру
        game_type = game_tracker.active_game
        game_tracker.end_game()
        
        # Сбрасываем состояния
        await safe_finish_state(state)
        
        await message.answer(
            f"✅ Игра успешно завершена!\n\n"
            f"Информация о завершенной игре:\n{game_info}"
        )
        logger.info(f"Игра {game_type} принудительно завершена пользователем {user_id} в чате {chat_id}")
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при завершении игры: {e}\n{error_traceback}")
        await message.answer("Произошла ошибка при завершении игры.") 