from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.utils.markdown import bold, text, italic
import datetime
import logging
import asyncio
import random
import traceback
import aiosqlite
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
import os
import json
from typing import Dict, List, Optional, Union, Tuple
from aiogram import Bot, Dispatcher, types
from aiogram.utils.emoji import emojize
from aiogram.types import ParseMode, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
import config
from config import ADMIN_ID, DB_PATH, INACTIVITY_THRESHOLD_DAYS, POINTS_PER_MESSAGE, POINTS_PER_REPLY
from database import Database, init_db, db
from games import EmojiGame, QuizGame
from jokes_facts import get_random_content

# Проверка импорта модуля schedule
try:
    from schedule import ScheduleManager
    # Создаем экземпляр менеджера расписания
    schedule_manager = ScheduleManager(DB_PATH)
except ImportError as e:
    logging.error(f"Ошибка импорта модуля schedule: {e}")
    schedule_manager = None

logger = logging.getLogger(__name__)

# Объявляем переменную bot, которая будет установлена из main.py
bot = None

# Состояния для FSM при создании события
class ScheduleStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_time = State()
    confirm_event = State()

# Функция для установки бота из main.py
def set_bot(bot_instance):
    global bot
    bot = bot_instance

# Функция для удаления команд бота
async def remove_bot_commands():
    """Удаляет все команды из меню бота"""
    if bot:
        await bot.delete_my_commands()
        logger.info("Команды бота успешно удалены")
    else:
        logger.error("Бот не инициализирован, невозможно удалить команды")
        raise ValueError("Bot instance is not set")

# Шаблоны сообщений для напоминаний
REMINDER_TEMPLATES = [
    "Привет! Мы скучаем по тебе в чате {chat_title}. Заходи поболтать!",
    "Эй! В чате {chat_title} давно не видно твоих сообщений. Возвращайся!",
    "Здравствуй! Участники чата {chat_title} ждут твоего возвращения!",
    "Привет! Загляни в {chat_title}, там проходят интересные обсуждения, которые тебе могут понравиться.",
    "Мы заметили, что ты давно не появлялся(ась) в чате {chat_title}. Надеемся скоро тебя увидеть!"
]

# Шаблоны предложений поиграть в игры
GAME_INVITATION_TEMPLATES = [
    "Кстати, в чате есть игры! Попробуй /emoji_game или /quiz, чтобы заработать дополнительные баллы активности!",
    "Знаешь ли ты, что можешь повысить свой ранг, участвуя в играх? Набери /emoji_game или /quiz в чате!",
    "Возвращайся и попробуй наши игры! Используй команды /emoji_game и /quiz прямо в чате.",
    "В чате появились новые игры! Проверь свои знания с /quiz или угадай по эмодзи с /emoji_game."
]

# Шаблоны сообщений о челлендже
CHALLENGE_TEMPLATES = [
    "Сегодня в чате проходит челлендж дня! Узнай подробности командой /challenge.",
    "Присоединяйся к ежедневному челленджу! Просто напиши /challenge в чате.",
    "Новый день - новый челлендж! Проверь командой /challenge и участвуй.",
    "Кстати, у нас есть ежедневные челленджи. Напиши /challenge, чтобы узнать задание на сегодня."
]

# Темы для ежедневного обсуждения
DAILY_TOPICS = [
    "🎮 **Игры**: Во что вы играли недавно? Какая игра вас приятно удивила?",
    "🎵 **Музыка**: Поделитесь треком или исполнителем, который вы слушаете на повторе в последнее время.",
    "📚 **Книги**: Какую книгу вы сейчас читаете или хотели бы начать читать?",
    "🎬 **Кино**: Что из последнего просмотренного вас впечатлило, а что разочаровало?",
    "🍕 **Еда**: Поделитесь своим любимым рецептом или местом, где вкусно готовят.",
    "💡 **Лайфхаки**: Какой лайфхак вы узнали недавно и он действительно работает?",
    "💪 **Достижения**: Чем вы гордитесь из того, что сделали на этой неделе?",
    "🧠 **Знания**: Расскажите об интересном факте, который вы недавно узнали.",
    "🔮 **Будущее**: Какую технологию будущего вы хотели бы увидеть уже сегодня?",
    "🏞️ **Путешествия**: Поделитесь своим любимым местом, куда можно поехать на выходные.",
    "🧩 **Хобби**: Какое хобби вы хотели бы попробовать, но ещё не решились?",
    "🎭 **Развлечения**: Какой фильм/сериал, выходящий в ближайшее время, вы ждёте больше всего?",
    "👾 **Технологии**: Какой гаджет изменил вашу жизнь к лучшему?",
    "🧘 **Саморазвитие**: Поделитесь советом, как справляться со стрессом.",
    "🎯 **Цели**: Какую цель вы хотите достичь в ближайшие 3 месяца?",
    "🤔 **Философия**: Если бы вы могли дать один совет себе из прошлого, что бы это было?",
    "🚀 **Мотивация**: Что вас мотивирует двигаться вперёд, когда всё идёт не по плану?",
    "🎁 **Подарки**: Какой самый запоминающийся подарок вы получали или дарили?",
    "👻 **Страхи**: Чего вы боялись в детстве, а сейчас это кажется забавным?",
    "🎨 **Творчество**: Если бы вы могли мгновенно освоить любой творческий навык, что бы выбрали?",
    "🏘️ **Дом**: Что для вас идеальный дом - место, дизайн, атмосфера?",
    "📱 **Приложения**: Какое нестандартное приложение вы можете порекомендовать?",
    "☕ **Утро**: Поделитесь своим утренним ритуалом, который помогает хорошо начать день.",
    "🌙 **Вечер**: Как вы любите проводить вечер после тяжёлого дня?",
    "🏆 **Успех**: Как для вас выглядит успешная жизнь?",
    "🤝 **Отношения**: Какую черту характера вы цените в людях больше всего?",
    "💭 **Мечты**: Если бы вы могли исполнить одно своё желание, что бы вы выбрали?",
    "📺 **Шоу**: Какое ток-шоу, стрим или подкаст вы рекомендуете посмотреть/послушать?",
    "🧪 **Эксперименты**: Какой смелый эксперимент со своей жизнью вы хотели бы провести?",
    "🌍 **Мир**: Какое место на Земле вы мечтаете посетить больше всего и почему?"
]

# Звания дня для самых активных пользователей
ACTIVE_USER_TITLES = [
    "🌟 Звезда чата",
    "👑 Король/Королева общения",
    "🔥 Пламенный собеседник",
    "💎 Бриллиант дискуссий",
    "🚀 Ракета активности",
    "🏆 Чемпион диалога",
    "⚡ Энергия общения",
    "🥇 Золотой голос чата",
    "🎯 Меткий собеседник",
    "🌈 Радуга эмоций",
    "💫 Сверхновая звезда",
    "🧠 Интеллектуальный титан",
    "🦄 Уникальный собеседник",
    "💼 Профессионал общения",
    "🔍 Внимательный наблюдатель"
]

# Список вопросов дня
RANDOM_QUESTIONS = [
    "⁉️ Если бы вы могли изменить одно решение в своей жизни, что бы это было?",
    "👥 Кто повлиял на вас больше всего и почему?",
    "💰 Если бы у вас был неограниченный бюджет на один день, как бы вы его потратили?",
    "🏝️ Куда бы вы отправились, если бы могли телепортироваться куда угодно прямо сейчас?",
    "📚 Какая книга изменила ваше мировоззрение?",
    "🧠 Верите ли вы в существование инопланетной жизни? Почему?",
    "⚔️ Какая историческая эпоха вам интересна больше всего?",
    "🍽️ Если бы вы могли есть только одно блюдо до конца жизни, что бы это было?",
    "😱 Что вас пугает больше всего?",
    "🤔 Считаете ли вы, что технологии делают нас ближе или отдаляют друг от друга?",
    "🎯 Достигли ли вы того, чего хотели 5 лет назад?",
    "🏢 Что бы вы изменили на своей работе, если бы могли?",
    "👻 Верите ли вы в паранормальные явления? Почему?",
    "🎭 Если бы ваша жизнь была фильмом, какой бы это был жанр?",
    "🌍 Какую глобальную проблему вы бы решили, если бы могли?",
    "🧩 Что для вас является самым сложным в общении с людьми?",
    "🔮 Каким вы видите мир через 20 лет?",
    "🚀 Какой была бы ваша сверхспособность, если бы вы могли выбрать любую?",
    "💯 Что вы цените в других людях больше всего?",
    "🧘‍♀️ Что помогает вам расслабиться после тяжелого дня?",
    "👶 Что бы вы рассказали своему 10-летнему себе?",
    "🌟 Кто ваш герой или кумир и почему?",
    "🏆 Какое достижение заставило вас почувствовать наибольшую гордость?",
    "💔 Как вы справляетесь с разочарованиями?",
    "🎁 Лучше дарить подарки или получать их?",
    "🚩 Что для вас является «красным флагом» в отношениях?",
    "🕒 Если бы у вас была возможность замедлить или ускорить время, что бы вы выбрали?",
    "💤 О чем вы мечтаете?",
    "❓ Что вы никогда не сможете понять?",
    "🔍 Что бы вы хотели узнать, прежде чем умереть?",
    "🎵 Какая песня лучше всего описывает вашу жизнь?",
    "🎪 Соревнование или сотрудничество — что вам ближе?",
    "🍀 Верите ли вы в удачу или считаете, что всё зависит только от наших решений?",
    "📱 Как бы вы выжили без интернета на месяц?",
    "👑 Если бы вы правили страной, что бы вы изменили первым делом?",
    "🧗‍♂️ Что было самым сложным испытанием в вашей жизни?",
    "📆 Отдаете ли вы предпочтение планированию или спонтанности?",
    "🎮 Какие три приложения/игры вы бы взяли на необитаемый остров?",
    "🙊 Если бы вы могли быть любым животным, каким бы вы были и почему?",
    "📱 Приносят ли социальные сети больше пользы или вреда?",
    "🧠 Если бы человечество могло решить только одну проблему в следующие 5 лет, что бы вы выбрали?",
    "🕵️ Какая тайна или загадка вас больше всего интригует?",
    "👨‍👩‍👧‍👦 Что самое важное в семье?",
    "🎓 Чему самому важному вы научились НЕ в школе?",
    "🚶‍♂️ Какой жизненный совет вы бы дали людям, которые моложе вас на 10 лет?",
    "👀 Что вам говорят о вас ваши друзья, но вы сами этого не замечаете?",
    "🗣️ Какое слово или фраза вас раздражает больше всего?",
    "💼 Если бы вы могли попробовать любую профессию на один день, что бы вы выбрали?",
    "⚖️ Справедливость или милосердие — что важнее?",
    "🧰 Какой навык вы хотели бы освоить, но ещё не нашли время?"
]

# Обработчик команды /start
async def cmd_start(message: types.Message):
    user = message.from_user
    await message.answer(f"Привет, {user.first_name}! 👋\n\n"
                         f"Я бот для повышения активности в чате. "
                         f"Я отслеживаю сообщения участников и награждаю баллами за активность.")


# Обработчик команды /help
async def cmd_help(message: types.Message):
    """Показывает список доступных команд бота"""
    help_text = (
        "🤖 *Список команд бота:*\n\n"
        
        "📊 *Активность и ранги:*\n"
        "/start - Начать использование бота\n"
        "/help - Показать это сообщение помощи\n"
        "/stats - Ваша статистика активности и ранг\n"
        "/top - Топ активных участников чата\n"
        "/challenge - Информация о текущем задании дня\n\n"
        
        "🎮 *Игры и развлечения:*\n"
        "/emoji_game - Игра \"Угадай по эмодзи\"\n"
        "/quiz - Викторина с разными вопросами\n"
        "/game_stats - Статистика игровой активности\n\n"
        
        "💬 *Вопросы дня:*\n"
        "/random_question - Задать случайный вопрос дня для обсуждения\n"
        "/question_stats - Статистика вопросов дня и ответов на них\n\n"
        
        "⚙️ *Настройки:*\n"
        "/empty - Очистить список команд из меню\n\n"
        
        "🏆 *Система рангов:*\n"
        "За активность в чате вы получаете баллы и повышаете свой ранг:\n"
        "• Сообщение: +1 балл\n"
        "• Длинное сообщение: +0.5 балла бонус\n"
        "• Медиа-контент: +0.7 балла бонус\n"
        "• Правильный ответ в игре: +1-5 баллов\n"
        "• Участие в обсуждении вопроса дня: +2 балла\n\n"
        
        "Чем выше ваш ранг, тем больше ваш статус в чате! 🌟"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


# Обработчик команды /stats
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Получаем статистику пользователя
    stats = await db.get_user_stats(chat_id, user_id)
    
    # Форматирование даты последней активности
    last_active = "Сегодня" if stats["last_active"] is None else stats["last_active"]
    
    # Информация о следующем ранге
    next_rank_info = ""
    if stats["next_rank"]:
        next_rank_info = (
            f"\n\n⏭️ *Следующий ранг:* {stats['next_rank']['name']}\n"
            f"📊 Нужно набрать: {stats['next_rank']['points_left']:.1f} баллов"
        )
    
    # Формируем текст ответа
    response = (
        f"📊 *Ваша статистика активности:*\n\n"
        f"👤 Пользователь: {message.from_user.full_name}\n"
        f"💬 Всего сообщений: {stats['total_messages']}\n"
        f"⭐ Баллы активности: {stats['total_points']:.1f}\n"
        f"🏆 Ранг: {stats['rank']}\n"
        f"🕒 Последняя активность: {last_active}"
        f"{next_rank_info}"
    )
    
    await message.answer(response, parse_mode="Markdown")


def escape_markdown(text):
    if not text:
        return ""
    return (
        text.replace("_", "\\_")
            .replace("*", "\\*")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
    )

# Обработчик команды /top
async def cmd_top(message: types.Message):
    chat_id = message.chat.id
    
    # Логирование для отладки
    logger.info(f"Запрошен топ пользователей для чата {chat_id}")
    
    # Проверяем, существует ли чат в базе данных
    await db.add_chat(chat_id, message.chat.title if hasattr(message.chat, 'title') else "Личный чат")
    
    # Получаем топ пользователей
    top_users = await db.get_top_users(chat_id)
    
    # Логирование количества найденных пользователей
    logger.info(f"Найдено {len(top_users) if top_users else 0} пользователей в топе для чата {chat_id}")
    
    # Если пользователей нет, выводим сообщение
    if not top_users:
        await message.answer("В этом чате пока нет активных пользователей.")
        return
    
    # Формируем ответ с топом пользователей
    response = f"🏆 *Топ {len(top_users)} активных участников чата:*\n\n"
    
    for i, user in enumerate(top_users, 1):
        user_id, username, first_name, last_name = user[0], user[1], user[2], user[3]
        total_points, total_messages = user[4], user[5]
        
        # Получаем ранг пользователя
        rank = await db.get_rank_by_points(total_points)
        
        # Формируем имя пользователя
        if first_name:
            name = first_name
            if last_name:
                name += f" {last_name}"
        else:
            name = f"User_{user_id}"
        
        # Добавляем username в скобках, если он доступен
        if username:
            name += f" (@{username})"
        
        # Экранируем все пользовательские данные
        name = escape_markdown(name)
        rank = escape_markdown(rank)
        
        # Добавляем медали для первых трех мест
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        else:
            medal = f"{i}. "
        
        response += f"{medal}{name}\n"
        response += f"   ⭐ {total_points:.1f} баллов | 💬 {total_messages} сообщений\n"
        response += f"   🏆 Ранг: {rank}\n\n"
    
    await message.answer(response, parse_mode="Markdown")


# Обработчик команды /challenge
async def cmd_challenge(message: types.Message):
    # Получаем текущий день недели
    day_of_week = datetime.datetime.now().weekday()
    
    challenges = {
        0: "📝 *Понедельник - день знакомства*\nРасскажите интересный факт о себе!",
        1: "❓ *Вторник - день вопросов*\nЗадайте интересный вопрос для обсуждения!",
        2: "🎮 *Среда - игровой день*\nУгадайте фильм/игру по эмодзи! 🕵️🔍⏰",
        3: "📚 *Четверг - день советов*\nПоделитесь полезным советом или лайфхаком!",
        4: "😂 *Пятница - день мемов*\nПоделитесь забавным мемом или историей!",
        5: "🔄 *Суббота - обратная связь*\nПоделитесь своим мнением о нашем чате!",
        6: "🎯 *Воскресенье - день целей*\nРасскажите о своих планах на неделю!"
    }
    
    await message.answer(challenges[day_of_week], parse_mode=types.ParseMode.MARKDOWN)


# Функция для проверки и отправки напоминаний неактивным пользователям
async def check_inactive_users(bot):
    """
    Проверяет наличие неактивных пользователей и тегает их в чате
    Возвращает общее количество отмеченных неактивных пользователей
    """
    try:
        logger.info("Запуск проверки неактивных пользователей")
        
        # Счетчик общего количества отмеченных неактивных пользователей
        total_inactive_marked = 0
        
        # Получаем все известные боту чаты
        chats = await db.get_all_chats()
        
        for chat_id, chat_title in chats:
            try:
                # Получаем список неактивных пользователей в данном чате
                inactive_users = await db.get_inactive_users(chat_id, INACTIVITY_THRESHOLD_DAYS)
                
                if not inactive_users:
                    logger.info(f"В чате {chat_id} ({chat_title}) нет неактивных пользователей")
                    continue
                
                logger.info(f"Найдено {len(inactive_users)} неактивных пользователей в чате {chat_id} ({chat_title})")
                
                # Сначала отправляем сообщение в сам чат о количестве неактивных
                try:
                    await bot.send_message(
                        chat_id,
                        f"🔍 Обнаружено {len(inactive_users)} неактивных участников."
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
                    continue
                
                # Счетчик отмеченных неактивных пользователей в текущем чате
                chat_inactive_marked = 0
                
                # Отправляем напоминания в чат, тегая каждого неактивного пользователя
                for user_id, username, first_name, last_name, last_active in inactive_users:
                    try:
                        # Только если у пользователя есть юзернейм, его можно тегнуть
                        if username:
                            # Формируем обращение к пользователю
                            user_tag = f"@{username}"
                            
                            # Выбираем случайный шаблон напоминания
                            reminder_message = random.choice(REMINDER_TEMPLATES).format(chat_title=chat_title)
                            
                            # Добавляем случайное приглашение в игру или челлендж
                            if random.random() < 0.5:
                                reminder_message += "\n\n" + random.choice(GAME_INVITATION_TEMPLATES)
                            else:
                                reminder_message += "\n\n" + random.choice(CHALLENGE_TEMPLATES)
                            
                            # Отправляем напоминание в чат с тегом пользователя
                            await bot.send_message(
                                chat_id,
                                f"{user_tag}, мы скучаем по тебе! {reminder_message}"
                            )
                            
                            logger.info(f"Отправлено напоминание пользователю {user_id} ({username}) в чат {chat_id}")
                            
                            # Увеличиваем счетчики отмеченных пользователей
                            chat_inactive_marked += 1
                            total_inactive_marked += 1
                            
                            # Небольшая задержка между отправками, чтобы не нагружать API
                            await asyncio.sleep(1)
                        else:
                            logger.warning(f"Пользователь {user_id} ({first_name}) не имеет username, невозможно тегнуть")
                            
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
                
                # Отправляем сообщение в чат о завершении рассылки
                try:
                    if chat_inactive_marked > 0:
                        await bot.send_message(
                            chat_id,
                            f"✅ Отмечено {chat_inactive_marked} неактивных участников."
                        )
                    else:
                        await bot.send_message(
                            chat_id,
                            f"ℹ️ Ни один участник не был отмечен (у всех отсутствует username)."
                        )
                except Exception as e:
                    logger.error(f"Не удалось отправить финальное сообщение в чат {chat_id}: {e}")
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке чата {chat_id}: {e}")
        
        logger.info(f"Проверка неактивных пользователей завершена. Всего отмечено: {total_inactive_marked}")
        return total_inactive_marked
        
    except Exception as e:
        logger.error(f"Критическая ошибка при проверке неактивных пользователей: {e}")
        return 0


# Команда для запуска проверки неактивных пользователей вручную (только для админов)
async def cmd_check_inactive(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("🔍 Запускаю проверку неактивных пользователей...")
    
    # Запускаем проверку
    from main import bot  # Импортируем бота из main.py
    
    # Сохраняем текущий чат, чтобы потом отправить итоговое сообщение
    current_chat_id = message.chat.id
    
    # Запускаем проверку и получаем информацию о количестве обработанных неактивных пользователей
    total_inactive_users = await check_inactive_users(bot)
    
    if total_inactive_users > 0:
        await message.answer(f"✅ Проверка завершена! Обнаружено и отмечено {total_inactive_users} неактивных участников.")
    else:
        await message.answer("✅ Проверка завершена! Неактивных участников не обнаружено.")


# Обработчик для всех обычных сообщений - будет вызываться только если ни один другой обработчик не сработал
async def process_message(message: types.Message):
    """Обработка всех текстовых сообщений в чате"""
    try:
        # Игнорируем сообщения из личных чатов
        if message.chat.type == 'private':
            return
            
        # Получаем информацию о пользователе
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        chat_id = message.chat.id
        chat_title = message.chat.title
        
        # Регистрируем чат и пользователя
        await db.add_chat(chat_id, chat_title)
        await db.add_user(user_id, username, first_name, last_name)
        
        # Определяем тип сообщения и начисляем баллы
        message_type = "text"
        points = POINTS_PER_MESSAGE  # Базовые баллы за сообщение
        
        # Проверяем, является ли сообщение ответом на вопрос дня
        if message.reply_to_message:
            question_info = await db.check_if_response_to_question(chat_id, message.reply_to_message.message_id)
            
            if question_info:
                # Сообщение является ответом на вопрос дня
                question_id = question_info['question_id']
                success, points_awarded = await db.add_question_response(question_id, user_id)
                
                if success:
                    # Уведомляем пользователя о начислении бонусных баллов
                    await message.reply(
                        f"✨ Спасибо за участие в обсуждении вопроса дня!\n"
                        f"Вы получили +{points_awarded} баллов активности.",
                        parse_mode=types.ParseMode.MARKDOWN
                    )
                    return  # Выходим, так как баллы уже начислены
        
        # Если это не ответ на вопрос или ответ не был успешно обработан, продолжаем обычное начисление баллов
        
        # Дополнительные баллы за длинные сообщения
        if message.text and len(message.text) > 100:
            points += 0.5
            message_type = "long_text"
        
        # Дополнительные баллы за медиа-контент
        if message.photo or message.video or message.document or message.audio:
            points += 0.7
            message_type = "media"
        
        # Дополнительные баллы за ответ другому пользователю
        if message.reply_to_message and not message.reply_to_message.from_user.is_bot:
            points += POINTS_PER_REPLY
            message_type = "reply"
        
        # Начисляем баллы и проверяем, изменился ли ранг
        rank_info = await db.add_activity(chat_id, user_id, message_type, points)
        
        # Уведомляем пользователя о повышении ранга, если он изменился
        if rank_info["is_rank_up"]:
            # Формируем текст уведомления о повышении ранга
            rank_up_text = (
                f"🎉 Поздравляем, {first_name}!\n\n"
                f"Вы достигли нового ранга: *{rank_info['new_rank']}*\n"
                f"Продолжайте в том же духе! 💪"
            )
            await message.reply(rank_up_text, parse_mode=types.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")


# Функция для отправки еженедельного отчета об активности
async def send_weekly_report(bot):
    """Отправляет еженедельный отчет об активности в каждый чат"""
    try:
        logger.info("Запуск отправки еженедельного отчета")
        
        # Получаем все известные боту чаты
        chats = await db.get_all_chats()
        
        for chat_id, chat_title in chats:
            try:
                # Получаем отчет об активности за последние 7 дней
                report = await db.get_chat_activity_report(chat_id, days=7)
                
                # Формируем текст отчета
                report_text = f"📊 *Еженедельный отчет активности чата*\n\n"
                report_text += f"📝 Всего сообщений: {report['message_count']}\n"
                report_text += f"⭐ Всего баллов: {report['total_points']:.1f}\n"
                report_text += f"👥 Активных участников: {report['active_users']}\n\n"
                
                # Добавляем статистику по дням
                report_text += "📅 *Активность по дням:*\n"
                
                for day, count in report['daily_activity']:
                    report_text += f"• {day}: {count} сообщений\n"
                
                # Получаем топ-5 активных участников
                top_users = await db.get_top_users(chat_id, limit=5)
                
                if top_users:
                    report_text += "\n🏆 *Самые активные участники недели:*\n"
                    
                    for i, (user_id, username, first_name, last_name, points, messages) in enumerate(top_users, 1):
                        name = username if username else (first_name + (" " + last_name if last_name else ""))
                        report_text += f"{i}. {name} - {points:.1f} баллов\n"
                
                # Отправляем отчет в чат
                await bot.send_message(
                    chat_id,
                    report_text,
                    parse_mode=types.ParseMode.MARKDOWN
                )
                
                logger.info(f"Отправлен еженедельный отчет в чат {chat_id} ({chat_title})")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке отчета в чат {chat_id}: {e}")
        
        logger.info("Отправка еженедельных отчетов завершена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке еженедельных отчетов: {e}")


# Команда для ручного запуска отправки отчета (только для админов)
async def cmd_send_report(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("📊 Запускаю формирование и отправку отчета активности...")
    
    # Запускаем отправку отчета
    from main import bot  # Импортируем бота из main.py
    await send_weekly_report(bot)
    
    await message.answer("✅ Отчет успешно отправлен!")


# Функция для отправки ежедневной темы для обсуждения
async def send_daily_topic(bot):
    """
    Отправляет ежедневную тему для обсуждения во все чаты
    """
    try:
        logger.info("Запуск отправки ежедневной темы для обсуждения")
        
        # Получаем все известные боту чаты
        chats = await db.get_all_chats()
        
        # Выбираем случайную тему из списка
        daily_topic = random.choice(DAILY_TOPICS)
        
        # Формируем сообщение
        message_text = f"💬 **Тема дня для обсуждения:**\n\n{daily_topic}\n\nПоделитесь своими мыслями в чате!"
        
        # Отправляем тему в каждый чат
        for chat_id, chat_title in chats:
            try:
                # Отправляем сообщение в чат
                await bot.send_message(
                    chat_id,
                    message_text,
                    parse_mode=types.ParseMode.MARKDOWN
                )
                
                logger.info(f"Тема дня отправлена в чат {chat_id} ({chat_title})")
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при отправке темы дня в чат {chat_id}: {e}")
        
        logger.info("Отправка ежедневной темы для обсуждения завершена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке ежедневной темы: {e}")


# Команда для ручной отправки ежедневной темы для обсуждения (только для админов)
async def cmd_send_daily_topic(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("💬 Отправляю тему дня для обсуждения...")
    
    # Запускаем отправку темы дня
    from main import bot  # Импортируем бота из main.py
    await send_daily_topic(bot)
    
    await message.answer("✅ Тема для обсуждения успешно отправлена!")


# Функция для определения и отправки звания дня самому активному пользователю
async def send_active_user_of_the_day(bot):
    """
    Определяет самого активного пользователя за последние 24 часа 
    и отправляет уведомление в чат
    """
    try:
        logger.info("Запуск определения самого активного пользователя дня")
        
        # Получаем все известные боту чаты
        chats = await db.get_all_chats()
        
        for chat_id, chat_title in chats:
            try:
                # Получаем самого активного пользователя
                active_user = await db.get_most_active_user_today(chat_id)
                
                if not active_user or active_user['message_count'] < 5:  # Минимальный порог - 5 сообщений
                    logger.info(f"В чате {chat_id} ({chat_title}) нет достаточно активных пользователей")
                    continue
                
                # Формируем имя пользователя
                user_name = active_user['username'] if active_user['username'] else (
                    active_user['first_name'] + (" " + active_user['last_name'] if active_user['last_name'] else ""))
                
                # Формируем тег пользователя для упоминания
                user_tag = f"@{active_user['username']}" if active_user['username'] else user_name
                
                # Выбираем случайное звание
                title = random.choice(ACTIVE_USER_TITLES)
                
                # Формируем сообщение
                message_text = (
                    f"📢 **Самый активный участник дня!**\n\n"
                    f"🏅 Звание: {title}\n"
                    f"👤 Пользователь: {user_tag}\n"
                    f"📊 Сообщений: {active_user['message_count']}\n"
                    f"⭐ Баллов активности: {active_user['total_points']:.1f}\n\n"
                    f"Поздравляем! Продолжайте в том же духе! 🎉"
                )
                
                # Отправляем сообщение в чат
                await bot.send_message(
                    chat_id,
                    message_text,
                    parse_mode=types.ParseMode.MARKDOWN
                )
                
                logger.info(f"Отправлено уведомление о самом активном пользователе дня в чат {chat_id}")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке чата {chat_id}: {e}")
        
        logger.info("Определение самого активного пользователя дня завершено")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при определении самого активного пользователя: {e}")


# Команда для ручной отправки объявления о самом активном участнике (только для админов)
async def cmd_active_user_of_day(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("🏆 Определяю самого активного пользователя дня...")
    
    # Запускаем определение и отправку
    from main import bot  # Импортируем бота из main.py
    await send_active_user_of_the_day(bot)
    
    await message.answer("✅ Информация о самом активном пользователе отправлена!")


# Обработчик команды /empty - для очистки списка команд бота
async def cmd_empty(message: types.Message):
    """Очищает список команд бота в интерфейсе Telegram"""
    try:
        # Очищаем список команд
        await remove_bot_commands()
        
        # Отправляем подтверждение
        await message.answer(
            "✅ Список команд бота очищен!\n\n"
            "Теперь вы можете использовать бота, вводя команды вручную, "
            "без отображения их в интерфейсе."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при очистке команд бота: {e}")
        await message.answer("❌ Произошла ошибка при очистке команд бота.")


# Обработчик присоединения новых пользователей к чату
async def on_new_chat_member(message: types.Message):
    """Приветствует новых участников чата с тегами для лучшей интеграции"""
    # Проверяем, что сообщение содержит информацию о новом участнике
    if not message.new_chat_members:
        return
    
    # Получаем информацию о чате
    chat_id = message.chat.id
    chat_title = message.chat.title
    
    # Приветствуем каждого нового участника
    for new_member in message.new_chat_members:
        # Пропускаем, если новый участник - это сам бот
        if new_member.is_bot and new_member.username == (await message.bot.me).username:
            continue
        
        # Формируем тег для пользователя
        user_tag = f"@{new_member.username}" if new_member.username else new_member.full_name
        
        # Формируем приветственное сообщение
        welcome_text = (
            f"👋 Привет, {user_tag}! Добро пожаловать в чат *{chat_title}*!\n\n"
            f"🔍 *Несколько полезных команд:*\n"
            f"• /help - Список всех команд\n"
            f"• /stats - Твоя статистика в чате\n"
            f"• /top - Самые активные участники\n"
            f"• /emoji_game - Сыграть в игру с эмодзи\n\n"
            f"💬 В этом чате твоя активность отслеживается и за неё начисляются баллы. "
            f"Чем больше общаешься, тем выше твой ранг!\n\n"
            f"🤝 Не стесняйся задавать вопросы и участвовать в обсуждениях. Мы рады тебя видеть!"
        )
        
        # Отправляем приветственное сообщение
        await message.answer(welcome_text, parse_mode="Markdown")
        
        # Регистрируем нового пользователя в базе данных
        try:
            await db.add_user(new_member.id, new_member.username, new_member.first_name, new_member.last_name)
            logger.info(f"Новый пользователь {new_member.id} ({user_tag}) добавлен в базу")
        except Exception as e:
            logger.error(f"Ошибка при добавлении нового пользователя в базу: {e}")


# Обработчик команды /game_stats - статистика игровой активности
async def cmd_game_stats(message: types.Message):
    """Показывает статистику игровой активности пользователя"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        # Получаем статистику пользователя (общая)
        stats = await db.get_user_stats(chat_id, user_id)
        
        # Получаем статистику игровой активности
        # Здесь можно добавить специфичный запрос для игровой статистики
        emoji_count = await db.get_activity_count(chat_id, user_id, "emoji_game")
        quiz_count = await db.get_activity_count(chat_id, user_id, "quiz")
        
        # Формируем ответ
        game_stats_text = (
            f"🎮 *Игровая статистика:*\n\n"
            f"👤 Пользователь: {message.from_user.full_name}\n\n"
            f"🎯 *Количество игр:*\n"
            f"• Эмодзи игры: {emoji_count} раз\n"
            f"• Викторины: {quiz_count} раз\n"
            f"• Всего игр: {emoji_count + quiz_count} раз\n\n"
            f"📊 *Рейтинг активности:*\n"
            f"• Текущий ранг: {stats['rank']}\n"
            f"• Всего баллов: {stats['total_points']:.1f}\n"
        )
        
        if stats["next_rank"]:
            game_stats_text += f"\n⏭️ До следующего ранга ({stats['next_rank']['name']}) осталось {stats['next_rank']['points_left']:.1f} баллов."
        
        await message.answer(game_stats_text, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Ошибка при получении игровой статистики: {e}")
        await message.answer("Произошла ошибка при получении игровой статистики. Попробуйте позже.")


# Обработчик команды /chat_info - информация о чате
async def cmd_chat_info(message: types.Message):
    """Показывает информацию о текущем чате"""
    try:
        # Проверяем, что команда вызвана администратором
        if message.from_user.id not in ADMIN_ID:
            await message.answer("❌ Эта команда доступна только администраторам.")
            return
        
        chat_id = message.chat.id
        chat = message.chat
        
        # Получаем статистику чата
        chat_stats = await db.get_chat_activity_report(chat_id, days=30)
        
        # Получаем количество пользователей в чате
        user_count = await db.get_chat_user_count(chat_id)
        
        # Получаем информацию о неактивных пользователях
        inactive_count = len(await db.get_inactive_users(chat_id, INACTIVITY_THRESHOLD_DAYS))
        
        # Формируем текст ответа
        response = (
            f"📊 *Информация о чате:*\n\n"
            f"🏷️ Название: {chat.title}\n"
            f"🆔 ID чата: `{chat_id}`\n"
            f"👥 Количество пользователей: {user_count}\n"
            f"📝 Сообщений за 30 дней: {chat_stats['message_count']}\n"
            f"⭐ Всего баллов активности: {chat_stats['total_points']:.1f}\n"
            f"🚶‍♂️ Неактивных пользователей: {inactive_count}\n"
            f"👤 Активных пользователей: {chat_stats['active_users']}\n\n"
        )
        
        # Добавляем информацию о статистике по дням
        if chat_stats['daily_activity']:
            response += "*Статистика по дням:*\n"
            for day, count in chat_stats['daily_activity'][-7:]:  # Последние 7 дней
                response += f"• {day}: {count} сообщений\n"
        
        await message.answer(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о чате: {e}")
        await message.answer("Произошла ошибка при получении информации о чате. Попробуйте позже.")


# Обработчик команды /admin - админ-панель
async def cmd_admin(message: types.Message):
    """Показывает административные команды"""
    try:
        # Проверяем, что команда вызвана администратором
        if message.from_user.id not in ADMIN_ID:
            await message.answer("❌ Эта команда доступна только администраторам.")
            return
        
        # Формируем список административных команд
        admin_commands = (
            f"🛠️ *Административные команды:*\n\n"
            f"/chat_info - Информация о текущем чате\n"
            f"/check_inactive - Проверить неактивных пользователей\n"
            f"/clean_inactive_users - Очистить базу от вышедших пользователей\n"
            f"/send_report - Отправить отчет об активности\n"
            f"/send_daily_topic - Отправить тему дня для обсуждения\n"
            f"/active_user_of_day - Объявить самого активного пользователя\n"
            f"/add_points - Начислить очки активности пользователю\n"
            f"/send_to_all - Отправить сообщение во все чаты\n"
        )
        
        await message.answer(admin_commands, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Ошибка при отображении админ-панели: {e}")
        await message.answer("Произошла ошибка при отображении админ-панели. Попробуйте позже.")


# Обработчик команды /send_to_all - отправка сообщения во все чаты
async def cmd_send_to_all(message: types.Message):
    """Отправляет сообщение во все чаты, где есть бот"""
    try:
        # Проверяем, что команда вызвана администратором
        if message.from_user.id not in ADMIN_ID:
            await message.answer("❌ Эта команда доступна только администраторам.")
            return
        
        # Получаем текст сообщения (после команды)
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.answer(
                "❌ Необходимо указать текст сообщения!\n\n"
                "Использование: /send_to_all [текст сообщения]"
            )
            return
        
        broadcast_text = command_parts[1]
        
        # Получаем список всех чатов
        chats = await db.get_all_chats()
        
        if not chats:
            await message.answer("❌ Нет чатов для отправки сообщения.")
            return
        
        # Запрашиваем подтверждение
        confirm_message = (
            f"📣 *Подтверждение отправки сообщения:*\n\n"
            f"Текст сообщения:\n{broadcast_text}\n\n"
            f"Количество чатов для отправки: {len(chats)}\n\n"
            f"Для подтверждения ответьте 'Подтверждаю' на это сообщение."
        )
        
        await message.answer(confirm_message, parse_mode="Markdown")
        
        # Здесь можно добавить логику ожидания подтверждения
        # Но для простоты пока просто отправляем сообщение о функциональности
        await message.answer(
            "⚠️ Функция массовой отправки находится в разработке. "
            "В текущей версии подтверждение не требуется, но сообщения не отправляются. "
            "Обратитесь к разработчику для полной реализации."
        )
    
    except Exception as e:
        logger.error(f"Ошибка при подготовке массовой отправки: {e}")
        await message.answer("Произошла ошибка при подготовке массовой отправки. Попробуйте позже.")


# Добавим метод в класс Database для получения количества определенных типов активности
async def get_activity_count(self, chat_id, user_id, activity_type):
    """Получает количество активностей определенного типа для пользователя"""
    try:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT COUNT(*) FROM activity WHERE chat_id = ? AND user_id = ? AND message_type = ?',
                (chat_id, user_id, activity_type)
            )
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logging.error(f"Ошибка при получении количества активностей: {e}")
        return 0

# Добавляем метод класса Database в объект db
setattr(db.__class__, 'get_activity_count', get_activity_count)


# Добавим метод в класс Database для получения количества пользователей в чате
async def get_chat_user_count(self, chat_id):
    """Получает общее количество уникальных пользователей в чате"""
    try:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT COUNT(DISTINCT user_id) FROM activity WHERE chat_id = ?',
                (chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logging.error(f"Ошибка при получении количества пользователей: {e}")
        return 0

# Добавляем метод класса Database в объект db
setattr(db.__class__, 'get_chat_user_count', get_chat_user_count)


# Функция регистрации всех обработчиков
def register_handlers(dp):
    """Регистрирует все обработчики команд и сообщений"""
    # Важно: порядок регистрации имеет значение!
    # Сначала регистрируем обработчики конкретных команд
    
    # Примечание: Игровые обработчики теперь регистрируются напрямую в main.py
    # для предотвращения циклических зависимостей
    
    # Базовые команды
    dp.register_message_handler(cmd_start, commands=["start"])
    dp.register_message_handler(cmd_help, commands=["help"])
    dp.register_message_handler(cmd_stats, commands=["stats"])
    dp.register_message_handler(cmd_top, commands=["top"])
    dp.register_message_handler(cmd_challenge, commands=["challenge"])
    dp.register_message_handler(cmd_game_stats, commands=["game_stats"])
    dp.register_message_handler(cmd_empty, commands=["empty"])
    
    # Новые команды - шутки и факты
    dp.register_message_handler(cmd_joke, commands=["joke"])
    dp.register_message_handler(cmd_fact, commands=["fact"])
    dp.register_message_handler(cmd_tech_fact, commands=["tech_fact"])
    dp.register_message_handler(cmd_random_content, commands=["random_content"])
    
    # Новые команды - расписание событий
    dp.register_message_handler(cmd_schedule, commands=["schedule"])
    dp.register_message_handler(cmd_create_event, commands=["create_event"])
    dp.register_message_handler(cmd_cancel_event_creation, commands=["cancel"], state=ScheduleStates)
    
    # Регистрация обработчиков состояний для создания события
    dp.register_message_handler(process_event_title, state=ScheduleStates.waiting_for_title)
    dp.register_message_handler(process_event_description, state=ScheduleStates.waiting_for_description)
    dp.register_message_handler(process_event_date, state=ScheduleStates.waiting_for_date)
    dp.register_message_handler(process_event_time, state=ScheduleStates.waiting_for_time)
    dp.register_message_handler(process_event_confirmation, state=ScheduleStates.confirm_event)
    
    # Регистрация обработчиков команд для работы с событиями
    dp.register_message_handler(cmd_view_event, regexp=r"^/event_\d+$")
    dp.register_message_handler(cmd_join_event, regexp=r"^/join_\d+$")
    dp.register_message_handler(cmd_leave_event, regexp=r"^/leave_\d+$")
    dp.register_message_handler(cmd_delete_event, regexp=r"^/delete_event_\d+$")
    
    # Административные команды
    dp.register_message_handler(cmd_chat_info, commands=["chat_info"])
    dp.register_message_handler(cmd_admin, commands=["admin"])
    dp.register_message_handler(cmd_send_to_all, commands=["send_to_all"])
    dp.register_message_handler(cmd_remove_user, commands=["remove_user"])  # Added remove_user command registration
    
    # Добавляем обработчик команды проверки неактивных
    dp.register_message_handler(cmd_check_inactive, Command("check_inactive"))
    
    # Добавляем обработчик команды отправки отчета
    dp.register_message_handler(cmd_send_report, Command("send_report"))
    
    # Добавляем обработчик команды отправки ежедневной темы
    dp.register_message_handler(cmd_send_daily_topic, Command("send_daily_topic"))
    
    # Добавляем обработчик команды активного пользователя
    dp.register_message_handler(cmd_active_user_of_day, Command("active_user_of_day"))
    
    # Добавляем обработчик команды очистки базы от вышедших пользователей
    dp.register_message_handler(cmd_clean_inactive_users, Command("clean_inactive_users"))
    
    # Обработчик новых участников в чате
    dp.register_message_handler(on_new_chat_member, content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
    
    # Обработчик ухода участников из чата
    dp.register_message_handler(on_left_chat_member, content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
    
    # Обработчик для всех остальных сообщений регистрируем в последнюю очередь
    dp.register_message_handler(process_message)

# Функция для отправки случайного вопроса дня
async def send_random_question(bot):
    """Отправляет случайный вопрос дня во все активные чаты"""
    try:
        logger.info("Запуск отправки случайного вопроса дня")
        
        # Получаем все известные боту чаты
        chats = await db.get_all_chats()
        
        # Выбираем случайный вопрос
        question = random.choice(RANDOM_QUESTIONS)
        
        # Формируем сообщение
        message_text = f"🎯 **Вопрос дня:**\n\n{question}\n\nПоделитесь своими мыслями в чате! 💭\n\n_За участие в обсуждении вы получите дополнительные баллы активности!_"
        
        # Счетчик успешных отправок
        successful_sends = 0
        
        # Отправляем вопрос в каждый чат
        for chat_id, chat_title in chats:
            try:
                # Отправляем сообщение в чат и сохраняем его ID
                message = await bot.send_message(
                    chat_id,
                    message_text,
                    parse_mode=types.ParseMode.MARKDOWN
                )
                
                # Сохраняем ID сообщения с вопросом в базе данных для отслеживания ответов
                await db.save_question_message_id(chat_id, message.message_id, question)
                
                logger.info(f"Вопрос дня отправлен в чат {chat_id} ({chat_title})")
                successful_sends += 1
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при отправке вопроса дня в чат {chat_id}: {e}")
        
        logger.info(f"Отправка случайного вопроса дня завершена. Успешно отправлено в {successful_sends} чатов")
        return successful_sends
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке случайного вопроса дня: {e}")
        return 0

# Команда для ручной отправки случайного вопроса дня (только для админов)
async def cmd_send_random_question(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("🎯 Отправляю случайный вопрос дня...")
    
    # Запускаем отправку вопроса дня
    from main import bot  # Импортируем бота из main.py
    count = await send_random_question(bot)
    
    await message.answer(f"✅ Случайный вопрос дня успешно отправлен в {count} чатов!")

# Команда для просмотра статистики вопросов дня
async def cmd_question_stats(message: types.Message):
    chat_id = message.chat.id
    
    # Получаем статистику вопросов для этого чата
    questions = await db.get_question_stats(chat_id)
    
    if not questions:
        await message.answer("В этом чате еще не было вопросов дня или на них никто не ответил.")
        return
    
    # Формируем ответ
    response = "📊 *Статистика последних вопросов дня:*\n\n"
    
    for i, q in enumerate(questions, 1):
        # Преобразуем timestamp в читабельную дату
        date_str = q['timestamp'].split(' ')[0] if ' ' in q['timestamp'] else q['timestamp']
        
        response += f"*{i}. {q['question']}*\n"
        response += f"📅 Дата: {date_str}\n"
        response += f"👥 Ответов: {q['response_count']}\n"
        response += f"⭐ Начислено баллов: {q['total_points']}\n"
        
        if q['participants']:
            response += "🙋‍♂️ Участники: " + ", ".join(q['participants'][:3])
            if len(q['participants']) > 3:
                response += f" и еще {len(q['participants']) - 3}"
            response += "\n"
        
        response += "\n"
    
    await message.answer(response, parse_mode=types.ParseMode.MARKDOWN)

# Обработчик команды /joke - получение случайной шутки
async def cmd_joke(message: types.Message):
    """Отправляет случайную шутку"""
    content = get_random_content("joke")
    await message.answer(f"{content['emoji']} *Шутка:*\n\n{content['content']}", parse_mode="Markdown")

# Обработчик команды /fact - получение случайного факта
async def cmd_fact(message: types.Message):
    """Отправляет случайный интересный факт"""
    content = get_random_content("fact")
    await message.answer(f"{content['emoji']} *Интересный факт:*\n\n{content['content']}", parse_mode="Markdown")

# Обработчик команды /tech_fact - получение случайного технического факта
async def cmd_tech_fact(message: types.Message):
    """Отправляет случайный технический факт"""
    content = get_random_content("tech")
    await message.answer(f"{content['emoji']} *Технический факт:*\n\n{content['content']}", parse_mode="Markdown")

# Обработчик команды /random_content - получение случайного контента (шутка или факт)
async def cmd_random_content(message: types.Message):
    """Отправляет случайный контент - шутку или факт"""
    content = get_random_content()
    
    if content['type'] == "joke":
        await message.answer(f"{content['emoji']} *Случайная шутка:*\n\n{content['content']}", parse_mode="Markdown")
    elif content['type'] == "fact":
        await message.answer(f"{content['emoji']} *Случайный факт:*\n\n{content['content']}", parse_mode="Markdown")
    elif content['type'] == "tech":
        await message.answer(f"{content['emoji']} *Случайный технический факт:*\n\n{content['content']}", parse_mode="Markdown")

# Обработчик команды /schedule - просмотр расписания событий чата
async def cmd_schedule(message: types.Message):
    """Показывает расписание предстоящих событий в чате"""
    chat_id = message.chat.id
    
    # Получаем список предстоящих событий
    events = await schedule_manager.get_chat_events(chat_id)
    
    if not events:
        await message.answer(
            "📅 *Расписание событий*\n\n"
            "В этом чате пока нет запланированных событий.\n\n"
            "Чтобы создать новое событие, используйте команду /create\\_event",
            parse_mode="Markdown"
        )
        return
    
    # Формируем список событий
    response = "📅 *Расписание предстоящих событий:*\n\n"
    
    for i, event in enumerate(events, 1):
        # Преобразуем время в читаемый формат
        event_time = datetime.datetime.fromisoformat(event['event_time'])
        formatted_date = event_time.strftime("%d.%m.%Y")
        formatted_time = event_time.strftime("%H:%M")
        
        # Формируем описание события
        response += f"*{i}. {event['title']}*\n"
        response += f"📆 Дата: {formatted_date}\n"
        response += f"🕒 Время: {formatted_time}\n"
        
        if event['description']:
            response += f"📝 Описание: {event['description']}\n"
        
        response += f"👥 Участников: {event['participant_count']}\n"
        response += f"/join\\_{event['id']} - присоединиться\n"
        response += f"/event\\_{event['id']} - подробнее\n\n"
    
    response += "Чтобы создать новое событие, используйте команду /create\\_event"
    
    await message.answer(response, parse_mode="Markdown")

# Обработчик команды /create_event - создание нового события
async def cmd_create_event(message: types.Message, state: FSMContext):
    """Начинает процесс создания нового события"""
    # Проверяем, что команда вызвана в групповом чате
    if message.chat.type == "private":
        await message.answer(
            "ℹ️ Создавать события можно только в групповых чатах.\n"
            "Перейдите в чат группы и используйте там команду /create\\_event"
        )
        return
    
    await ScheduleStates.waiting_for_title.set()
    await state.update_data(chat_id=message.chat.id, creator_id=message.from_user.id)
    
    await message.answer(
        "📅 *Создание нового события*\n\n"
        "Шаг 1/4: Введите название события (до 100 символов)\n\n"
        "Чтобы отменить создание, отправьте /cancel",
        parse_mode="Markdown"
    )

# Обработчик отмены создания события
async def cmd_cancel_event_creation(message: types.Message, state: FSMContext):
    """Отменяет процесс создания нового события"""
    try:
        current_state = await state.get_state()
        
        if current_state is None:
            return
        
        # Если пользователь находится в одном из состояний создания события
        if current_state.startswith('ScheduleStates'):
            # Попробуем сбросить состояние безопасно
            try:
                await state.reset_state(with_data=True)
            except Exception as e:
                logger.error(f"Ошибка при сбросе состояния: {e}")
            
            await message.answer("❌ Создание события отменено.")
    except Exception as e:
        logger.error(f"Ошибка при отмене создания события: {e}")
        await message.answer("❌ Создание события отменено.")

# Обработчик для получения названия события
async def process_event_title(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия события"""
    title = message.text.strip()
    
    # Проверка длины названия
    if len(title) > 100:
        await message.answer(
            "⚠️ Название слишком длинное. Пожалуйста, введите название до 100 символов."
        )
        return
    
    # Сохраняем название и переходим к следующему шагу
    await state.update_data(title=title)
    await ScheduleStates.waiting_for_description.set()
    
    await message.answer(
        "📝 *Шаг 2/4: Введите описание события*\n\n"
        "Это поле необязательное. Если вы не хотите добавлять описание, отправьте '-'.\n\n"
        "Чтобы отменить создание, отправьте /cancel",
        parse_mode="Markdown"
    )

# Обработчик для получения описания события
async def process_event_description(message: types.Message, state: FSMContext):
    """Обрабатывает ввод описания события"""
    description = message.text.strip()
    
    # Если пользователь не хочет добавлять описание
    if description == "-":
        description = None
    
    # Сохраняем описание и переходим к следующему шагу
    await state.update_data(description=description)
    await ScheduleStates.waiting_for_date.set()
    
    await message.answer(
        "📆 *Шаг 3/4: Введите дату события*\n\n"
        "Формат: ДД.ММ.ГГГГ (например, 25.12.2023)\n\n"
        "Чтобы отменить создание, отправьте /cancel",
        parse_mode="Markdown"
    )

# Обработчик для получения даты события
async def process_event_date(message: types.Message, state: FSMContext):
    """Обрабатывает ввод даты события"""
    date_str = message.text.strip()
    
    try:
        # Пытаемся преобразовать строку в дату
        event_date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        
        # Проверяем, что дата не в прошлом
        if event_date < datetime.date.today():
            await message.answer(
                "⚠️ Дата не может быть в прошлом. Пожалуйста, введите корректную дату."
            )
            return
        
        # Сохраняем дату и переходим к следующему шагу
        await state.update_data(event_date=event_date)
        await ScheduleStates.waiting_for_time.set()
        
        await message.answer(
            "🕒 *Шаг 4/4: Введите время события*\n\n"
            "Формат: ЧЧ:ММ (например, 18:30)\n\n"
            "Чтобы отменить создание, отправьте /cancel",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ (например, 25.12.2023)"
        )

# Обработчик для получения времени события
async def process_event_time(message: types.Message, state: FSMContext):
    """Обрабатывает ввод времени события"""
    time_str = message.text.strip()
    
    try:
        # Пытаемся преобразовать строку во время
        event_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        
        # Получаем данные из состояния
        data = await state.get_data()
        event_date = data['event_date']
        
        # Объединяем дату и время
        full_datetime = datetime.datetime.combine(event_date, event_time)
        
        # Проверяем, что дата и время не в прошлом
        if full_datetime < datetime.datetime.now():
            await message.answer(
                "⚠️ Время события не может быть в прошлом. Пожалуйста, введите корректное время."
            )
            return
        
        # Сохраняем полное время и переходим к подтверждению
        await state.update_data(event_datetime=full_datetime)
        await ScheduleStates.confirm_event.set()
        
        # Формируем сообщение для подтверждения
        confirm_message = (
            "📋 *Подтвердите создание события:*\n\n"
            f"Название: {data['title']}\n"
        )
        
        if data['description']:
            confirm_message += f"Описание: {data['description']}\n"
        
        confirm_message += (
            f"Дата: {event_date.strftime('%d.%m.%Y')}\n"
            f"Время: {event_time.strftime('%H:%M')}\n\n"
            "Для подтверждения отправьте 'Подтвердить'.\n"
            "Для отмены отправьте 'Отмена' или /cancel"
        )
        
        await message.answer(confirm_message, parse_mode="Markdown")
        
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ (например, 18:30)"
        )

# Обработчик для подтверждения создания события
async def process_event_confirmation(message: types.Message, state: FSMContext):
    """Обрабатывает подтверждение создания события"""
    response = message.text.strip().lower()
    
    if response == "подтвердить":
        # Получаем все данные из состояния
        data = await state.get_data()
        
        try:
            # Создаем событие в базе данных
            event_id = await schedule_manager.add_event(
                data['chat_id'],
                data['creator_id'],
                data['title'],
                data['description'],
                data['event_datetime']
            )
            
            # Добавляем создателя как первого участника
            await schedule_manager.add_participant(
                event_id,
                data['creator_id'],
                message.from_user.username
            )
            
            # Отправляем уведомление о создании события
            event_time = data['event_datetime']
            formatted_date = event_time.strftime("%d.%m.%Y")
            formatted_time = event_time.strftime("%H:%M")
            
            success_message = (
                "✅ *Событие успешно создано!*\n\n"
                f"📌 *{data['title']}*\n"
                f"📆 Дата: {formatted_date}\n"
                f"🕒 Время: {formatted_time}\n"
            )
            
            if data['description']:
                success_message += f"📝 Описание: {data['description']}\n"
            
            success_message += (
                f"\nID события: {event_id}\n"
                f"Чтобы присоединиться, используйте команду /join\\_{event_id}\n"
                f"Чтобы посмотреть детали, используйте команду /event\\_{event_id}"
            )
            
            await message.answer(success_message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка при создании события: {e}")
            await message.answer(
                "❌ Произошла ошибка при создании события. Пожалуйста, попробуйте еще раз."
            )
            
        finally:
            # Завершаем состояние в любом случае
            await state.finish()
            
    elif response == "отмена":
        await state.finish()
        await message.answer("❌ Создание события отменено.")
    else:
        await message.answer(
            "⚠️ Пожалуйста, отправьте 'Подтвердить' для создания события или 'Отмена' для отмены."
        )

# Обработчик для просмотра деталей события по команде /event_ID
async def cmd_view_event(message: types.Message):
    """Показывает подробную информацию о событии"""
    # Извлекаем ID события из команды
    command_parts = message.text.split('_')
    if len(command_parts) != 2:
        return
    
    try:
        event_id = int(command_parts[1])
        
        # Получаем информацию о событии
        event = await schedule_manager.get_event(event_id)
        
        if not event:
            await message.answer("⚠️ Событие не найдено или было удалено.")
            return
        
        # Проверяем, что событие принадлежит этому чату
        if event['chat_id'] != message.chat.id:
            return
        
        # Преобразуем время в читаемый формат
        event_time = datetime.datetime.fromisoformat(event['event_time'])
        formatted_date = event_time.strftime("%d.%m.%Y")
        formatted_time = event_time.strftime("%H:%M")
        
        # Формируем подробное описание события
        response = f"📌 *{event['title']}*\n\n"
        
        if event['description']:
            response += f"📝 *Описание:* {event['description']}\n\n"
        
        response += (
            f"📆 *Дата:* {formatted_date}\n"
            f"🕒 *Время:* {formatted_time}\n"
        )
        
        # Добавляем информацию о создателе
        # Для этого нужно получить данные о пользователе из базы
        creator_info = f"👤 *Организатор:* {event['creator_id']}\n\n"
        try:
            creator = await bot.get_chat_member(message.chat.id, event['creator_id'])
            if creator and creator.user:
                creator_name = creator.user.full_name
                creator_username = f" (@{creator.user.username})" if creator.user.username else ""
                creator_info = f"👤 *Организатор:* {creator_name}{creator_username}\n\n"
        except Exception as e:
            logger.error(f"Ошибка при получении информации о создателе события: {e}")
        
        response += creator_info
        
        # Добавляем список участников
        participants = event['participants']
        participant_count = len(participants)
        
        response += f"👥 *Участники ({participant_count}):*\n"
        
        if participant_count > 0:
            for i, participant in enumerate(participants, 1):
                username = participant['username'] or f"ID: {participant['user_id']}"
                response += f"{i}. {username}\n"
        else:
            response += "Пока никто не присоединился.\n"
        
        # Добавляем кнопки действий
        response += (
            f"\n/join_{event_id} - присоединиться к событию\n"
            f"/leave_{event_id} - отказаться от участия\n"
        )
        
        # Если пользователь является создателем события, добавляем кнопку удаления
        if message.from_user.id == event['creator_id'] or message.from_user.id in ADMIN_ID:
            response += f"/delete_event_{event_id} - удалить событие\n"
        
        await message.answer(response, parse_mode="Markdown")
        
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при просмотре события: {e}")
        await message.answer("⚠️ Произошла ошибка при получении информации о событии.")

# Обработчик для присоединения к событию по команде /join_ID
async def cmd_join_event(message: types.Message):
    """Позволяет пользователю присоединиться к событию"""
    # Извлекаем ID события из команды
    command_parts = message.text.split('_')
    if len(command_parts) != 2:
        return
    
    try:
        event_id = int(command_parts[1])
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Получаем информацию о событии для проверки
        event = await schedule_manager.get_event(event_id)
        
        if not event:
            await message.answer("⚠️ Событие не найдено или было удалено.")
            return
        
        # Проверяем, что событие принадлежит этому чату
        if event['chat_id'] != message.chat.id:
            return
        
        # Проверяем, не присоединился ли пользователь уже
        for participant in event['participants']:
            if participant['user_id'] == user_id:
                await message.answer("ℹ️ Вы уже присоединились к этому событию.")
                return
        
        # Добавляем пользователя как участника
        success = await schedule_manager.add_participant(event_id, user_id, username)
        
        if success:
            await message.answer(
                f"✅ Вы успешно присоединились к событию *{event['title']}*.\n"
                f"Чтобы посмотреть детали, используйте команду /event\\_{event_id}",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ Не удалось присоединиться к событию. Возможно, оно было удалено."
            )
            
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при присоединении к событию: {e}")
        await message.answer("⚠️ Произошла ошибка при присоединении к событию.")

# Обработчик для отказа от участия в событии по команде /leave_ID
async def cmd_leave_event(message: types.Message):
    """Позволяет пользователю отказаться от участия в событии"""
    # Извлекаем ID события из команды
    command_parts = message.text.split('_')
    if len(command_parts) != 2:
        return
    
    try:
        event_id = int(command_parts[1])
        user_id = message.from_user.id
        
        # Получаем информацию о событии для проверки
        event = await schedule_manager.get_event(event_id)
        
        if not event:
            await message.answer("⚠️ Событие не найдено или было удалено.")
            return
        
        # Проверяем, что событие принадлежит этому чату
        if event['chat_id'] != message.chat.id:
            return
        
        # Проверяем, является ли пользователь создателем события
        if event['creator_id'] == user_id:
            await message.answer(
                "⚠️ Вы являетесь организатором этого события и не можете отказаться от участия.\n"
                f"Если вы хотите отменить событие, используйте команду /delete_event_{event_id}"
            )
            return
        
        # Удаляем пользователя из участников
        success = await schedule_manager.remove_participant(event_id, user_id)
        
        if success:
            await message.answer(
                f"✅ Вы успешно отказались от участия в событии *{event['title']}*.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "ℹ️ Вы не являетесь участником этого события."
            )
            
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при отказе от участия в событии: {e}")
        await message.answer("⚠️ Произошла ошибка при отказе от участия в событии.")

# Обработчик для удаления события по команде /delete_event_ID
async def cmd_delete_event(message: types.Message):
    """Позволяет создателю или администратору удалить событие"""
    # Извлекаем ID события из команды
    command_parts = message.text.split('_')
    if len(command_parts) != 3:
        return
    
    try:
        event_id = int(command_parts[2])
        user_id = message.from_user.id
        
        # Получаем информацию о событии для проверки
        event = await schedule_manager.get_event(event_id)
        
        if not event:
            await message.answer("⚠️ Событие не найдено или уже было удалено.")
            return
        
        # Проверяем, что событие принадлежит этому чату
        if event['chat_id'] != message.chat.id:
            return
        
        # Проверяем права на удаление (создатель или администратор)
        if event['creator_id'] != user_id and user_id not in ADMIN_ID:
            await message.answer(
                "⚠️ У вас нет прав для удаления этого события.\n"
                "Только организатор события или администратор может его удалить."
            )
            return
        
        # Удаляем событие
        success = await schedule_manager.delete_event(event_id)
        
        if success:
            await message.answer(
                f"✅ Событие *{event['title']}* успешно удалено.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ Не удалось удалить событие. Пожалуйста, попробуйте еще раз."
            )
            
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при удалении события: {e}")
        await message.answer("⚠️ Произошла ошибка при удалении события.")

# Функция для отправки уведомлений о предстоящих событиях
async def send_event_notifications(bot):
    """Отправляет уведомления о предстоящих событиях"""
    try:
        logger.info("Проверка предстоящих событий для отправки уведомлений")
        
        # Получаем события, которые произойдут в ближайшие 6 часов
        upcoming_events = await schedule_manager.get_upcoming_events(within_hours=6)
        
        if not upcoming_events:
            logger.info("Нет предстоящих событий для уведомления")
            return
        
        logger.info(f"Найдено {len(upcoming_events)} предстоящих событий для уведомления")
        
        for event in upcoming_events:
            try:
                # Получаем список участников
                participants = await schedule_manager.get_participants(event['id'])
                
                # Преобразуем время события в удобный формат
                event_time = datetime.datetime.fromisoformat(event['event_time'])
                formatted_date = event_time.strftime("%d.%m.%Y")
                formatted_time = event_time.strftime("%H:%M")
                
                # Вычисляем, сколько времени осталось до события
                now = datetime.datetime.now()
                time_left = event_time - now
                hours_left = time_left.seconds // 3600
                minutes_left = (time_left.seconds % 3600) // 60
                
                time_remaining = f"{hours_left} ч {minutes_left} мин"
                
                # Формируем текст уведомления
                notification_text = (
                    f"⏰ *Напоминание о предстоящем событии!*\n\n"
                    f"📌 *{event['title']}*\n"
                    f"📆 Дата: {formatted_date}\n"
                    f"🕒 Время: {formatted_time}\n"
                    f"⏳ Осталось: {time_remaining}\n"
                )
                
                if event['description']:
                    notification_text += f"📝 Описание: {event['description']}\n"
                
                notification_text += f"\n👥 *Участники ({len(participants)}):*\n"
                
                # Отправляем основное уведомление сначала
                await bot.send_message(
                    event['chat_id'],
                    notification_text,
                    parse_mode="Markdown"
                )
                
                # Добавляем список участников с тегами отдельным сообщением
                if participants:
                    mentions = ""
                    for participant in participants:
                        if participant['username']:
                            mentions += f"@{participant['username']} "
                    
                    if mentions:
                        # Отправляем упоминания отдельным сообщением без Markdown
                        await bot.send_message(event['chat_id'], mentions)
                
                # Отправляем информацию о командах отдельным сообщением
                command_text = f"Чтобы посмотреть детали события, используйте команду /event\\_{event['id']}"
                await bot.send_message(
                    event['chat_id'],
                    command_text,
                    parse_mode="Markdown"
                )
                
                # Отмечаем, что уведомление отправлено
                await schedule_manager.mark_notification_sent(event['id'])
                
                logger.info(f"Отправлено уведомление о событии ID {event['id']} в чат {event['chat_id']}")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления о событии {event['id']}: {e}")
        
        logger.info("Проверка и отправка уведомлений о событиях завершена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке уведомлений о событиях: {e}")

# Функция планировщика для отправки уведомлений о предстоящих событиях
async def schedule_event_notifications():
    """Планировщик для регулярной проверки и отправки уведомлений о событиях"""
    while True:
        try:
            # Проверяем и отправляем уведомления
            await send_event_notifications(bot)
            
            # Проверяем каждые 30 минут
            await asyncio.sleep(30 * 60)
        except Exception as e:
            logger.error(f"Ошибка в планировщике уведомлений о событиях: {e}")
            await asyncio.sleep(60)  # В случае ошибки ждем 1 минуту

# Сообщения для стимуляции активности
ACTIVITY_MESSAGES = [
    "Что-то тихо тут стало! Давайте немного пообщаемся? 💭",
    "Время для новой темы! Кто хочет начать интересную дискуссию? 🎯",
    "Эй, как насчет немного оживить чат? 🚀",
    "Тишина... Но не в нашем чате! Кто готов поделиться чем-нибудь интересным? ✨",
    "Кажется, все заняты. Но, может, найдется минутка для общения? 🙂"
]

# Функция для отправки приглашения случайным пользователям, когда чат неактивен
async def invite_random_users_to_chat(bot):
    """Приглашает случайных пользователей к общению, если в чате затишье"""
    try:
        logger.info("Проверка активности в чатах")
        
        # Получаем все чаты
        chats = await db.get_all_chats()
        
        for chat_id, chat_title in chats:
            try:
                # Проверяем время последней активности в чате
                last_message_time = await db.get_last_activity_time(chat_id)
                
                if not last_message_time:
                    logger.info(f"В чате {chat_id} ({chat_title}) нет сообщений")
                    continue
                
                now = datetime.datetime.now()
                # Преобразуем строку времени в объект datetime
                try:
                    last_message_datetime = datetime.datetime.strptime(last_message_time, '%Y-%m-%d %H:%M:%S')
                except:
                    # В случае проблем с форматом просто проверяем текущую дату
                    last_message_datetime = now - datetime.timedelta(minutes=59)  # По умолчанию считаем, что сообщение было недавно
                
                # Проверяем прошло ли больше часа с последнего сообщения
                time_diff = now - last_message_datetime
                if time_diff.total_seconds() >= 3600:  # 3600 секунд = 1 час
                    logger.info(f"Чат {chat_id} ({chat_title}) неактивен более часа. Последнее сообщение: {last_message_time}")
                    
                    # Получаем случайных 5 пользователей чата
                    users = await db.get_random_chat_users(chat_id, 5)
                    
                    if not users or len(users) < 2:  # Нужно хотя бы 2 пользователя для стимуляции общения
                        logger.info(f"Недостаточно пользователей в чате {chat_id}")
                        continue
                    
                    # Формируем упоминания пользователей
                    user_mentions = []
                    for user_id, username, first_name, last_name in users:
                        if username:
                            user_mentions.append(f"@{username}")
                        else:
                            # Если нет username, то используем имя
                            user_name = first_name
                            if last_name:
                                user_name += f" {last_name}"
                            user_mentions.append(user_name)
                    
                    # Случайное сообщение для стимуляции активности
                    activity_message = random.choice(ACTIVITY_MESSAGES)
                    
                    # Формируем основное сообщение (без контента)
                    message = f"{activity_message}\n\n{', '.join(user_mentions)}, как насчёт обсудить что-нибудь интересное?"
                    
                    try:
                        # Отправляем основное сообщение
                        await bot.send_message(chat_id, message)
                        
                        # Добавляем случайную шутку/факт как отдельное сообщение
                        content = get_random_content()
                        
                        if content['type'] == "joke":
                            content_message = f"{content['emoji']} *Шутка:*\n\n{content['content']}"
                        elif content['type'] == "fact":
                            content_message = f"{content['emoji']} *Факт:*\n\n{content['content']}"
                        elif content['type'] == "tech":
                            content_message = f"{content['emoji']} *Tech:*\n\n{content['content']}"
                        
                        # Отправляем контент отдельным сообщением
                        await bot.send_message(chat_id, content_message, parse_mode="Markdown")
                        logger.info(f"Отправлено приглашение к активности в чат {chat_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке приглашения в чат {chat_id}: {e}")
                        # Пробуем отправить без разметки в случае ошибки
                        try:
                            await bot.send_message(chat_id, message)
                        except:
                            logger.error(f"Не удалось отправить сообщение в чат {chat_id} даже без разметки")
                else:
                    logger.debug(f"Чат {chat_id} активен. Последнее сообщение {time_diff.total_seconds()/60:.1f} минут назад")
            
            except Exception as e:
                logger.error(f"Ошибка при проверке активности чата {chat_id}: {e}")
                continue
        
        logger.info("Проверка активности в чатах завершена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при проверке активности чатов: {e}")

# Обработчик ухода участников из чата
async def on_left_chat_member(message: types.Message):
    """Удаляет покинувших участников из базы данных бота"""
    if not message.left_chat_member:
        return
    
    # Получаем информацию о пользователе и чате
    left_user = message.left_chat_member
    chat_id = message.chat.id
    
    # Пропускаем, если ушедший участник - это сам бот
    if left_user.is_bot and left_user.username == (await message.bot.me).username:
        return
    
    # Удаляем пользователя из базы данных для текущего чата
    try:
        success = await db.remove_user_from_chat(left_user.id, chat_id)
        
        if success:
            logger.info(f"Пользователь {left_user.id} ({left_user.full_name}) удален из базы для чата {chat_id}")
            
            # Удаляем пользователя из будущих событий в чате
            if schedule_manager:
                # Получаем все события чата
                events = await schedule_manager.get_chat_events(chat_id)
                for event in events:
                    # Удаляем пользователя из всех событий
                    await schedule_manager.remove_participant(event['id'], left_user.id)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя {left_user.id} из базы: {e}")

# Обработчик команды /clean_inactive_users для очистки базы от вышедших пользователей
async def cmd_clean_inactive_users(message: types.Message):
    """Очищает базу данных от пользователей, которые больше не состоят в чате"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("🧹 Начинаю проверку и очистку базы данных от вышедших пользователей...")
    
    try:
        # Получаем список всех пользователей в базе для этого чата
        async with aiosqlite.connect(DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row  # Используем Row для удобства доступа к полям
            cursor = await conn.execute('''
                SELECT DISTINCT u.user_id, u.username, u.first_name, u.last_name 
                FROM users u
                JOIN activity a ON u.user_id = a.user_id
                WHERE a.chat_id = ?
            ''', (chat_id,))
            
            users = await cursor.fetchall()
            
            user_count = len(users)
            await message.answer(f"📊 Найдено {user_count} пользователей в базе данных для этого чата.")
        
        # Счетчики
        removed_count = 0
        error_count = 0
        still_in_chat = 0
        
        # Статус-сообщение, которое будем обновлять
        status_message = await message.answer("⏳ Проверка пользователей... (0/{})".format(user_count))
        
        # Проверяем каждого пользователя
        for i, user_row in enumerate(users, 1):
            current_user_id = user_row['user_id']
            username = user_row['username']
            first_name = user_row['first_name']
            
            # Обновляем статус каждые 5 пользователей
            if i % 5 == 0 or i == len(users):
                try:
                    await bot.edit_message_text(
                        f"⏳ Проверка пользователей... ({i}/{user_count})", 
                        chat_id=chat_id, 
                        message_id=status_message.message_id
                    )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении статуса: {e}")
            
            try:
                # Пропускаем администраторов
                if current_user_id in ADMIN_ID:
                    logger.info(f"Пропускаем администратора {current_user_id}")
                    continue
                    
                # Получаем информацию о пользователе в чате
                user_is_in_chat = True
                try:
                    chat_member = await bot.get_chat_member(chat_id, current_user_id)
                    # Проверяем статус - left или kicked означает, что пользователя нет в чате
                    if chat_member.status in ['left', 'kicked']:
                        user_is_in_chat = False
                        logger.info(f"Пользователь {current_user_id} имеет статус {chat_member.status}")
                except Exception as e:
                    # Если ошибка при получении информации - скорее всего пользователь вышел
                    logger.info(f"Не удалось получить информацию о пользователе {current_user_id} в чате {chat_id}: {e}")
                    user_is_in_chat = False
                
                # Если пользователь вышел или его аккаунт удален
                if not user_is_in_chat:
                    # Удаляем пользователя из базы для этого чата
                    success = await db.remove_user_from_chat(current_user_id, chat_id)
                    
                    user_display = f"{first_name} (@{username})" if username else f"{first_name} ({current_user_id})"
                    logger.info(f"Удаление пользователя {user_display}: {'успешно' if success else 'неудачно'}")
                    
                    if success:
                        removed_count += 1
                        # Удаляем пользователя из всех событий
                        if schedule_manager:
                            try:
                                events = await schedule_manager.get_chat_events(chat_id)
                                for event in events:
                                    await schedule_manager.remove_participant(event['id'], current_user_id)
                            except Exception as e:
                                logger.error(f"Ошибка при удалении пользователя из событий: {e}")
                else:
                    still_in_chat += 1
                
            except Exception as e:
                logger.error(f"Ошибка при проверке пользователя {current_user_id}: {e}")
                error_count += 1
        
        # Отправляем отчет о результатах
        result_message = (
            f"✅ Очистка базы данных завершена!\n\n"
            f"📊 Результаты:\n"
            f"• Всего пользователей в базе: {user_count}\n"
            f"• Остались в чате: {still_in_chat}\n"
            f"• Удалено пользователей: {removed_count}\n"
            f"• Ошибок при проверке: {error_count}\n\n"
            f"База данных обновлена и содержит только актуальных участников чата."
        )
        
        # Пытаемся обновить статус-сообщение, если не получится - отправим новое
        try:
            await bot.edit_message_text(result_message, chat_id=chat_id, message_id=status_message.message_id)
        except:
            await message.answer(result_message)
        
    except Exception as e:
        logger.error(f"Ошибка при очистке базы данных: {e}")
        await message.answer(f"❌ Произошла ошибка при очистке базы данных: {str(e)}")

# Обработчик команды /add_points для начисления очков активности
async def cmd_add_points(message: types.Message):
    """Начисляет очки активности пользователю (только для администраторов)"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    # Разбор аргументов команды
    command_args = message.get_args().split()
    if not command_args or len(command_args) > 2:
        await message.answer("❌ Неверный формат команды. Используйте: /add_points <points> в ответ на сообщение или /add_points <user_id> <points>")
        return
    
    try:
        # Определяем ID пользователя и количество очков в зависимости от формата команды
        if len(command_args) == 1:
            # Если команда в формате "/add_points <points>" (отправлена в ответ на сообщение)
            if not message.reply_to_message:
                await message.answer("❌ Чтобы начислить очки, ответьте на сообщение пользователя командой /add_points <points>")
                return
                
            points_to_add = float(command_args[0])
            target_user_id = message.reply_to_message.from_user.id
            
            # Не начисляем очки боту
            if message.reply_to_message.from_user.is_bot:
                await message.answer("❌ Невозможно начислить очки боту.")
                return
        else:
            # Если команда в формате "/add_points <user_id> <points>"
            target_user_id = int(command_args[0])
            points_to_add = float(command_args[1])
        
        # Проверяем, что количество очков положительное
        if points_to_add <= 0:
            await message.answer("❌ Количество очков должно быть положительным числом.")
            return
        
        # Убедимся, что пользователь существует в базе данных
        await db.add_chat(chat_id, message.chat.title if hasattr(message.chat, 'title') else "Личный чат")
        
        # Получаем информацию о пользователе
        if message.reply_to_message:
            username = message.reply_to_message.from_user.username
            first_name = message.reply_to_message.from_user.first_name
            last_name = message.reply_to_message.from_user.last_name
        else:
            # Если нет ответа на сообщение, пробуем получить информацию из чата
            try:
                chat_member = await message.bot.get_chat_member(chat_id, target_user_id)
                username = chat_member.user.username
                first_name = chat_member.user.first_name
                last_name = chat_member.user.last_name
            except:
                # Если не удалось получить информацию, используем заглушки
                username = None
                first_name = f"User_{target_user_id}"
                last_name = None
        
        # Добавляем пользователя в базу или обновляем его информацию
        await db.add_user(target_user_id, username, first_name, last_name)
            
        # Добавляем очки активности пользователю
        rank_info = await db.add_activity(chat_id, target_user_id, "manual_addition", points_to_add)
        
        # Формируем сообщение об успешном начислении очков
        user_mention = f"[пользователю](tg://user?id={target_user_id})"
        response = f"✅ Успешно добавлено {points_to_add} очков {user_mention}."
        
        # Если произошло повышение ранга, добавляем информацию
        if rank_info and rank_info.get('is_rank_up', False):
            old_rank = rank_info.get('old_rank', '')
            new_rank = rank_info.get('new_rank', '')
            total_points = rank_info.get('total_points', 0)
            
            response += f"\n\n🎖 *Повышение ранга!*\n📊 Набрано {total_points:.1f} баллов\n📈 Прошлый ранг: {old_rank}\n✨ Новый ранг: {new_rank}\n🎉 Поздравляем с достижением!"
        
        await message.answer(response, parse_mode="Markdown")
        
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя или количества очков.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении очков пользователю: {e}")
        await message.answer("❌ Произошла ошибка при добавлении очков. Попробуйте позже.")

# Обработчик команды /remove_user
async def cmd_remove_user(message: types.Message):
    """Удаляет пользователя из базы данных по ID (только для администраторов)"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Логируем попытку использования команды
    logger.info(f"Попытка использования команды /remove_user в чате {chat_id} пользователем {user_id}")
    
    # Проверяем, является ли пользователь администратором
    if user_id not in ADMIN_ID:
        logger.warning(f"Пользователь {user_id} попытался использовать команду /remove_user без прав администратора")
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    # Разбор аргументов команды
    command_args = message.get_args().split()
    if not command_args or len(command_args) != 1:
        logger.warning(f"Неверный формат команды /remove_user от пользователя {user_id}: {message.text}")
        await message.answer("❌ Неверный формат команды. Используйте: /remove_user <user_id>")
        return
    
    try:
        target_user_id = int(command_args[0])
        logger.info(f"Администратор {user_id} пытается удалить пользователя {target_user_id} из чата {chat_id}")
        
        # Удаляем пользователя из базы данных
        success = await db.remove_user_from_chat(target_user_id, chat_id)
        
        if success:
            logger.info(f"Пользователь {target_user_id} успешно удален из базы данных для чата {chat_id}")
            
            # Удаляем пользователя из всех событий в чате
            if schedule_manager:
                try:
                    events = await schedule_manager.get_chat_events(chat_id)
                    for event in events:
                        await schedule_manager.remove_participant(event['id'], target_user_id)
                    logger.info(f"Пользователь {target_user_id} удален из всех событий в чате {chat_id}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении пользователя {target_user_id} из событий: {e}")
            
            await message.answer(f"✅ Пользователь {target_user_id} успешно удален из базы данных и всех событий чата.")
        else:
            logger.error(f"Не удалось удалить пользователя {target_user_id} из базы данных для чата {chat_id}")
            await message.answer(f"❌ Не удалось удалить пользователя {target_user_id} из базы данных.")
            
    except ValueError:
        logger.error(f"Неверный формат ID пользователя в команде /remove_user: {command_args[0]}")
        await message.answer("❌ Неверный формат ID пользователя. ID должен быть числом.")
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды /remove_user: {e}")
        await message.answer("❌ Произошла ошибка при выполнении команды.")
