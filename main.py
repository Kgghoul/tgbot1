import asyncio
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
import aiojobs
import datetime
import random
import handlers

from config import BOT_TOKEN, TOKEN, BOT_USERNAME, ADMIN_ID
from database import init_db, db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Изменено с INFO на DEBUG для более подробных логов
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Импортируем модули после инициализации бота
# Важно импортировать здесь, чтобы избежать циклических зависимостей
from games import cmd_emoji_game, cmd_quiz, cmd_end_game, cmd_set_cooldown, GameStates, process_emoji_answer, process_quiz_answer
from handlers import (cmd_start, cmd_help, cmd_stats, cmd_top, cmd_challenge, cmd_game_stats, 
                     cmd_chat_info, cmd_admin, cmd_send_to_all, cmd_check_inactive, cmd_send_report, 
                     cmd_send_daily_topic, cmd_active_user_of_day, cmd_empty, on_new_chat_member, on_left_chat_member, process_message,
                     cmd_send_random_question, cmd_question_stats, cmd_clean_inactive_users,
                     # Новые команды
                     cmd_joke, cmd_fact, cmd_tech_fact, cmd_random_content,
                     cmd_schedule, cmd_create_event, cmd_cancel_event_creation,
                     process_event_title, process_event_description, process_event_date, process_event_time,
                     process_event_confirmation, cmd_view_event, cmd_join_event, cmd_leave_event, cmd_delete_event,
                     ScheduleStates, send_event_notifications, schedule_event_notifications, cmd_add_points)

# Устанавливаем экземпляр бота в модуль handlers
handlers.set_bot(bot)

# Команды бота для отображения в меню
BOT_COMMANDS = [
    types.BotCommand(command="start", description="Начать использование бота"),
    types.BotCommand(command="help", description="Помощь по командам бота"),
    types.BotCommand(command="stats", description="Ваша статистика активности"),
    types.BotCommand(command="top", description="Топ активных участников"),
    types.BotCommand(command="challenge", description="Текущий челлендж"),
    types.BotCommand(command="emoji_game", description="Игра \"Угадай по эмодзи\""),
    types.BotCommand(command="quiz", description="Викторина с вопросами"),
    types.BotCommand(command="game_stats", description="Статистика игр"),
    types.BotCommand(command="random_question", description="Задать случайный вопрос дня"),
    types.BotCommand(command="question_stats", description="Статистика вопросов дня"),
    # Новые команды
    types.BotCommand(command="joke", description="Получить случайную шутку"),
    types.BotCommand(command="fact", description="Получить интересный факт"),
    types.BotCommand(command="tech_fact", description="Получить технический факт"),
    types.BotCommand(command="random_content", description="Случайный контент (шутка/факт)"),
    types.BotCommand(command="schedule", description="Расписание событий чата"),
    types.BotCommand(command="create_event", description="Создать новое событие"),
    types.BotCommand(command="empty", description="Очистить список команд бота"),
]

# Установка команд для бота
async def set_bot_commands():
    await bot.set_my_commands(BOT_COMMANDS)
    logger.info("Команды бота успешно установлены")

# Удаление команд для бота
async def remove_bot_commands():
    await bot.delete_my_commands()
    logger.info("Команды бота успешно удалены")

# Глобальный планировщик для регулярных задач
scheduler = None

# Запуск проверки неактивных пользователей по расписанию
async def schedule_inactive_reminders():
    """Планировщик для регулярной проверки неактивных пользователей"""
    while True:
        try:
            # Получаем текущее время
            now = datetime.datetime.now()
            # Добавляем смещение для перевода в астанинское время (UTC+6)
            astana_time = now + datetime.timedelta(hours=6)
            
            # Запускаем проверку неактивных пользователей каждый день в 10:00 по Астане
            if astana_time.hour == 10 and astana_time.minute == 0:
                logger.info("Запуск проверки неактивных пользователей по расписанию (10:00 по Астане)")
                await handlers.check_inactive_users(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике проверки неактивных пользователей: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Запуск еженедельного отчета по расписанию
async def schedule_weekly_reports():
    """Планировщик для отправки еженедельного отчета об активности"""
    while True:
        try:
            # Получаем текущее время и день недели
            now = datetime.datetime.now()
            # Добавляем смещение для перевода в астанинское время (UTC+6)
            astana_time = now + datetime.timedelta(hours=6)
            
            # Отправляем отчет каждый понедельник в 9:00 по Астане
            if astana_time.weekday() == 0 and astana_time.hour == 9 and astana_time.minute == 0:
                logger.info("Запуск отправки еженедельного отчета по расписанию (9:00 понедельник по Астане)")
                await handlers.send_weekly_report(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике еженедельных отчетов: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Запуск ежедневной темы для обсуждения по расписанию
async def schedule_daily_topics():
    """Планировщик для отправки ежедневной темы для обсуждения"""
    while True:
        try:
            # Получаем текущее время
            now = datetime.datetime.now()
            # Добавляем смещение для перевода в астанинское время (UTC+6)
            astana_time = now + datetime.timedelta(hours=6)
            
            # Отправляем тему для обсуждения каждый день в 12:00 по Астане
            if astana_time.hour == 12 and astana_time.minute == 0:
                logger.info("Запуск отправки ежедневной темы для обсуждения по расписанию (12:00 по Астане)")
                await handlers.send_daily_topic(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике ежедневных тем: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Запуск определения активного пользователя дня по расписанию
async def schedule_active_user_of_day():
    """Планировщик для определения и объявления активного пользователя дня"""
    while True:
        try:
            # Получаем текущее время
            now = datetime.datetime.now()
            # Добавляем смещение для перевода в астанинское время (UTC+6)
            astana_time = now + datetime.timedelta(hours=6)
            
            # Определяем активного пользователя каждый день в 20:00 по Астане
            if astana_time.hour == 20 and astana_time.minute == 0:
                logger.info("Запуск определения активного пользователя дня по расписанию (20:00 по Астане)")
                await handlers.send_active_user_of_the_day(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике активного пользователя дня: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Запуск отправки случайных вопросов дня
async def schedule_random_questions():
    """Планировщик для отправки случайных вопросов дня в случайное время"""
    while True:
        try:
            # Получаем текущее время
            now = datetime.datetime.now()
            # Добавляем смещение для перевода в астанинское время (UTC+6)
            astana_time = now + datetime.timedelta(hours=6)
            
            # Определяем случайные часы для отправки (с 10:00 до 19:00 по Астане)
            # Это генерируется один раз в день и затем используется весь день
            # Используем день года как seed для воспроизводимости
            day_of_year = astana_time.timetuple().tm_yday
            random.seed(day_of_year)
            random_hour = random.randint(10, 19)
            random_minute = random.randint(0, 59)
            
            # Сбрасываем seed для других случайных операций
            random.seed()
            
            logger.debug(f"Сегодня случайный вопрос будет отправлен в {random_hour}:{random_minute:02d} по Астане")
            
            # Отправляем вопрос в определенное случайное время по Астане
            if astana_time.hour == random_hour and astana_time.minute == random_minute:
                logger.info(f"Запуск отправки случайного вопроса дня по расписанию в {astana_time.hour}:{astana_time.minute:02d} по Астане")
                await handlers.send_random_question(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике случайных вопросов дня: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Планировщик проверки активности чатов
async def schedule_chat_activity_check():
    """Планировщик для проверки активности в чатах и вызова случайных пользователей"""
    while True:
        try:
            logger.debug("Проверка активности в чатах")
            
            # Запускаем проверку каждые 15 минут
            await handlers.invite_random_users_to_chat(bot)
            
            # Ждем 15 минут до следующей проверки
            await asyncio.sleep(15 * 60)  # 15 минут
        except Exception as e:
            logger.error(f"Ошибка в планировщике проверки активности чатов: {e}")
            await asyncio.sleep(60)  # В случае ошибки ждем 1 минуту

# Прямая регистрация игровых обработчиков
logger.info("Регистрация игровых обработчиков...")
# Регистрация команд для игр
dp.register_message_handler(cmd_emoji_game, commands=["emoji_game"], state="*")
dp.register_message_handler(cmd_quiz, commands=["quiz"], state="*")
dp.register_message_handler(cmd_end_game, commands=["end_game"], state="*")
dp.register_message_handler(cmd_set_cooldown, commands=["set_cooldown"], state="*")

# Регистрация обработчиков состояний для игр
dp.register_message_handler(process_emoji_answer, state=GameStates.emoji_game)
dp.register_message_handler(process_quiz_answer, state=GameStates.quiz_game)

# Регистрация основных обработчиков напрямую
logger.info("Регистрация обработчиков команд...")
dp.register_message_handler(cmd_start, commands=["start"])
dp.register_message_handler(cmd_help, commands=["help"])
dp.register_message_handler(cmd_stats, commands=["stats"])
dp.register_message_handler(cmd_top, commands=["top"])
dp.register_message_handler(cmd_challenge, commands=["challenge"])
dp.register_message_handler(cmd_game_stats, commands=["game_stats"])
dp.register_message_handler(cmd_empty, commands=["empty"])
dp.register_message_handler(cmd_send_random_question, commands=["random_question"])
dp.register_message_handler(cmd_question_stats, commands=["question_stats"])

# Новые команды - шутки/факты
dp.register_message_handler(cmd_joke, commands=["joke"])
dp.register_message_handler(cmd_fact, commands=["fact"])
dp.register_message_handler(cmd_tech_fact, commands=["tech_fact"])
dp.register_message_handler(cmd_random_content, commands=["random_content"])

# Новые команды - расписание событий
dp.register_message_handler(cmd_schedule, commands=["schedule"])
dp.register_message_handler(cmd_create_event, commands=["create_event"], state=None)
dp.register_message_handler(cmd_cancel_event_creation, commands=["cancel"], state=ScheduleStates)

# Обработчики состояний для создания события
dp.register_message_handler(process_event_title, state=ScheduleStates.waiting_for_title)
dp.register_message_handler(process_event_description, state=ScheduleStates.waiting_for_description)
dp.register_message_handler(process_event_date, state=ScheduleStates.waiting_for_date)
dp.register_message_handler(process_event_time, state=ScheduleStates.waiting_for_time)
dp.register_message_handler(process_event_confirmation, state=ScheduleStates.confirm_event)

# Обработчики команд для работы с событиями
dp.register_message_handler(cmd_view_event, regexp=r"^/event_\d+$")
dp.register_message_handler(cmd_join_event, regexp=r"^/join_\d+$")
dp.register_message_handler(cmd_leave_event, regexp=r"^/leave_\d+$")
dp.register_message_handler(cmd_delete_event, regexp=r"^/delete_event_\d+$")

# Административные команды
dp.register_message_handler(cmd_chat_info, commands=["chat_info"])
dp.register_message_handler(cmd_admin, commands=["admin"])
dp.register_message_handler(cmd_send_to_all, commands=["send_to_all"])
dp.register_message_handler(cmd_check_inactive, commands=["check_inactive"])
dp.register_message_handler(cmd_send_report, commands=["send_report"])
dp.register_message_handler(cmd_send_daily_topic, commands=["send_daily_topic"])
dp.register_message_handler(cmd_active_user_of_day, commands=["active_user_of_day"])
dp.register_message_handler(cmd_clean_inactive_users, commands=["clean_inactive_users"])
dp.register_message_handler(cmd_add_points, commands=["add_points"])

# Обработчик новых участников в чате
dp.register_message_handler(on_new_chat_member, content_types=types.ContentTypes.NEW_CHAT_MEMBERS)

# Обработчик ухода участников из чата
dp.register_message_handler(on_left_chat_member, content_types=types.ContentTypes.LEFT_CHAT_MEMBER)

# Обработчик для всех остальных сообщений (должен быть в последнюю очередь)
dp.register_message_handler(process_message)

# Тестовая команда для проверки базовой работы
@dp.message_handler(commands=["test"])
async def cmd_test(message: types.Message):
    logger.info("Выполнение тестовой команды")
    await message.answer("Тестовая команда работает!")

async def on_startup(dispatcher):
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    await init_db()
    
    logger.info("Установка команд бота...")
    await set_bot_commands()
    
    logger.info(f"Бот @{BOT_USERNAME} успешно запущен!")
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"Имя бота: {bot_info.username}")
    logger.info(f"ID бота: {bot_info.id}")
    
    # Вывод доступных команд
    my_commands = await bot.get_my_commands()
    for cmd in my_commands:
        logger.info(f"Зарегистрированная команда: /{cmd.command} - {cmd.description}")
    
    # Запуск планировщика для регулярных задач
    global scheduler
    scheduler = await aiojobs.create_scheduler()
    
    # Добавляем регулярные задачи в планировщик
    await scheduler.spawn(schedule_inactive_reminders())
    await scheduler.spawn(schedule_weekly_reports())
    await scheduler.spawn(schedule_daily_topics())
    await scheduler.spawn(schedule_active_user_of_day())
    await scheduler.spawn(schedule_random_questions())
    await scheduler.spawn(schedule_event_notifications())
    await scheduler.spawn(schedule_chat_activity_check())
    
    logger.info("Планировщик регулярных задач успешно запущен")

async def on_shutdown(dispatcher):
    """Действия при остановке бота"""
    logger.warning("Завершение работы...")
    
    # Закрываем планировщик
    if scheduler:
        await scheduler.close()
    
    logger.info("Планировщик остановлен")
    logger.info("Бот остановлен")
    
    # Закрываем соединения и сессии
    await bot.close()
    await storage.close()

# Добавление отладочного обработчика в самом конце, с низким приоритетом
@dp.message_handler(lambda message: True, content_types=types.ContentTypes.ANY)
async def debug_all_messages(message: types.Message):
    # Выводим детальную информацию о полученном сообщении
    logger.warning(f"⚠️ Необработанное сообщение: {message.text} от пользователя {message.from_user.id} ({message.from_user.username})")
    logger.warning(f"Тип чата: {message.chat.type}, ID чата: {message.chat.id}")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    ) 