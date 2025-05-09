import asyncio
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import aiojobs
import datetime
from aiogram.dispatcher import FSMContext

from config import BOT_TOKEN, TOKEN, BOT_USERNAME, ADMIN_ID
from database import init_db, db
from games import register_game_handlers, cmd_emoji_game  # Импортируем напрямую для тестирования
from handlers import (
    register_handlers, check_inactive_users, send_weekly_report, send_daily_topic, send_active_user_of_the_day,
    cmd_start, cmd_help, cmd_stats, cmd_top, cmd_challenge, 
    cmd_game_stats, cmd_chat_info, cmd_admin, cmd_send_to_all,
    process_emoji_game_answer, process_message, cmd_empty
)

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

# Команды бота для отображения в меню
BOT_COMMANDS = [
    types.BotCommand(command="start", description="Начать использование бота"),
    types.BotCommand(command="help", description="Помощь и список команд"),
    types.BotCommand(command="stats", description="Статистика активности"),
    types.BotCommand(command="top", description="Топ активных участников"),
    types.BotCommand(command="challenge", description="Текущий челлендж"),
    types.BotCommand(command="emoji_game", description="Игра \"Угадай по эмодзи\""),
    types.BotCommand(command="quiz", description="Викторина с вопросами"),
    types.BotCommand(command="game_stats", description="Статистика игр"),
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

# Прямая регистрация команды emoji_game для гарантии, регистрируем первой для приоритета
dp.register_message_handler(cmd_emoji_game, commands=["emoji_game"], state="*")

# Регистрация игровых обработчиков перед основными для приоритета
register_game_handlers(dp)
register_handlers(dp)

# Глобальный планировщик для регулярных задач
scheduler = None

# Запуск проверки неактивных пользователей по расписанию
async def schedule_inactive_reminders():
    """Планировщик для регулярной проверки неактивных пользователей"""
    while True:
        try:
            # Получаем текущее время
            now = datetime.datetime.now()
            
            # Запускаем проверку неактивных пользователей каждый день в 10:00
            if now.hour == 10 and now.minute == 0:
                logger.info("Запуск проверки неактивных пользователей по расписанию")
                await check_inactive_users(bot)
            
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
            
            # Отправляем отчет каждый понедельник в 9:00
            if now.weekday() == 0 and now.hour == 9 and now.minute == 0:
                logger.info("Запуск отправки еженедельного отчета по расписанию")
                await send_weekly_report(bot)
            
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
            
            # Отправляем тему для обсуждения каждый день в 12:00
            if now.hour == 12 and now.minute == 0:
                logger.info("Запуск отправки ежедневной темы для обсуждения по расписанию")
                await send_daily_topic(bot)
            
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
            
            # Определяем активного пользователя каждый день в 20:00
            if now.hour == 20 and now.minute == 0:
                logger.info("Запуск определения активного пользователя дня по расписанию")
                await send_active_user_of_the_day(bot)
            
            # Ждем 60 секунд до следующей проверки
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике активного пользователя дня: {e}")
            await asyncio.sleep(60)  # В случае ошибки также ждем 60 секунд

# Тестовая команда для проверки базовой работы
@dp.message_handler(commands=["test"])
async def cmd_test(message: types.Message):
    logger.info("Выполнение тестовой команды")
    await message.answer("Тестовая команда работает!")

async def on_startup(dispatcher):
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    await init_db()
    
    logger.info("Регистрация обработчиков команд...")
    register_handlers(dispatcher)
    
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
    
    # Если это команда /emoji_game, которая почему-то не была обработана
    if message.text and message.text.startswith('/emoji_game'):
        logger.error("Команда /emoji_game не была обработана основным обработчиком!")
        try:
            # Пробуем выполнить обработчик напрямую
            await message.answer("Пытаюсь запустить игру 'Угадай по эмодзи' напрямую...")
            await cmd_emoji_game(message, dp.current_state())
        except Exception as e:
            logger.exception(f"Ошибка при прямом вызове обработчика: {e}")

if __name__ == '__main__':
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    ) 