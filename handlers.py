from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.utils.markdown import bold, text, italic
import datetime
import logging
import asyncio
import random
import traceback
import aiosqlite

from config import POINTS_PER_MESSAGE, POINTS_PER_REPLY, ADMIN_ID, INACTIVITY_THRESHOLD_DAYS
from database import db

logger = logging.getLogger(__name__)

# Объявляем переменную bot, которая будет установлена из main.py
bot = None

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
        
        "⚙️ *Настройки:*\n"
        "/empty - Очистить список команд из меню\n\n"
        
        "🏆 *Система рангов:*\n"
        "За активность в чате вы получаете баллы и повышаете свой ранг:\n"
        "• Сообщение: +1 балл\n"
        "• Длинное сообщение: +0.5 балла бонус\n"
        "• Медиа-контент: +0.7 балла бонус\n"
        "• Правильный ответ в игре: +1-5 баллов\n\n"
        
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


# Обработчик команды /top
async def cmd_top(message: types.Message):
    chat_id = message.chat.id
    
    # Получаем топ пользователей
    top_users = await db.get_top_users(chat_id)
    
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
        name = first_name
        if last_name:
            name += f" {last_name}"
        if username:
            name += f" (@{username})"
            
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
            
        response += f"{medal}*{name}*\n"
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
        
        # Начисляем баллы за сообщение
        points = 1.0  # Базовое количество баллов
        
        # Бонус за длинное сообщение
        if len(message.text) > 100:
            points += 0.5
            
        # Бонус за медиа-контент
        if message.photo or message.video or message.animation or message.document:
            points += 0.7
            
        # Записываем активность и получаем информацию о возможном повышении ранга
        rank_info = await db.add_activity(chat_id, user_id, 'message', points)
        
        # Если произошло повышение ранга, отправляем поздравление
        if rank_info and rank_info.get('is_rank_up'):
            old_rank = rank_info.get('old_rank')
            new_rank = rank_info.get('new_rank')
            total_points = rank_info.get('total_points')
            
            # Анимированное поздравление при повышении ранга
            congrats_text = (
                f"🎖 *Повышение ранга!* 🎖\n\n"
                f"👤 {message.from_user.full_name}\n"
                f"📊 Набрано {total_points:.1f} баллов\n"
                f"📈 Прошлый ранг: {old_rank}\n"
                f"✨ Новый ранг: {new_rank}\n\n"
                f"🎉 Поздравляем с достижением!"
            )
            
            await message.answer(congrats_text, parse_mode="Markdown")
        
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
            f"/send_report - Отправить отчет об активности\n"
            f"/send_daily_topic - Отправить тему дня для обсуждения\n"
            f"/active_user_of_day - Объявить самого активного пользователя\n"
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
    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            'SELECT COUNT(*) FROM activity WHERE chat_id = ? AND user_id = ? AND message_type = ?',
            (chat_id, user_id, activity_type)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

# Добавляем метод класса Database в объект db
setattr(db.__class__, 'get_activity_count', get_activity_count)


# Добавим метод в класс Database для получения количества пользователей в чате
async def get_chat_user_count(self, chat_id):
    """Получает общее количество уникальных пользователей в чате"""
    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            'SELECT COUNT(DISTINCT user_id) FROM activity WHERE chat_id = ?',
            (chat_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

# Добавляем метод класса Database в объект db
setattr(db.__class__, 'get_chat_user_count', get_chat_user_count)


# Функция регистрации всех обработчиков
def register_handlers(dp):
    """Регистрирует все обработчики команд и сообщений"""
    # Важно: порядок регистрации имеет значение!
    # Сначала регистрируем обработчики конкретных команд
    
    # Базовые команды
    dp.register_message_handler(cmd_start, commands=["start"])
    dp.register_message_handler(cmd_help, commands=["help"])
    dp.register_message_handler(cmd_stats, commands=["stats"])
    dp.register_message_handler(cmd_top, commands=["top"])
    dp.register_message_handler(cmd_challenge, commands=["challenge"])
    dp.register_message_handler(cmd_game_stats, commands=["game_stats"])
    dp.register_message_handler(cmd_empty, commands=["empty"])
    
    # Административные команды
    dp.register_message_handler(cmd_chat_info, commands=["chat_info"])
    dp.register_message_handler(cmd_admin, commands=["admin"])
    dp.register_message_handler(cmd_send_to_all, commands=["send_to_all"])
    
    # Обработчик новых участников в чате
    dp.register_message_handler(on_new_chat_member, content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
    
    # Добавляем обработчик команды проверки неактивных
    dp.register_message_handler(cmd_check_inactive, Command("check_inactive"))
    
    # Добавляем обработчик команды отправки отчета
    dp.register_message_handler(cmd_send_report, Command("send_report"))
    
    # Добавляем обработчик команды отправки ежедневной темы
    dp.register_message_handler(cmd_send_daily_topic, Command("send_daily_topic"))
    
    # Добавляем обработчик команды активного пользователя
    dp.register_message_handler(cmd_active_user_of_day, Command("active_user_of_day"))
    
    # Обработчик для всех остальных сообщений регистрируем в последнюю очередь
    dp.register_message_handler(process_message) 