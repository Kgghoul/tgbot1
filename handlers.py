from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.utils.markdown import bold, text, italic
import datetime
import logging
import asyncio
import random

from config import POINTS_PER_MESSAGE, POINTS_PER_REPLY, ADMIN_IDS, INACTIVITY_THRESHOLD_DAYS
from database import db

logger = logging.getLogger(__name__)

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
    commands = [
        "/stats - ваша статистика активности",
        "/top - топ активных участников",
        "/challenge - текущий челлендж",
        "/emoji_game - игра 'Угадай по эмодзи'",
        "/quiz - викторина с вопросами",
        "/help - помощь и список команд"
    ]
    
    await message.answer("Доступные команды:\n\n" + "\n".join(commands))


# Обработчик команды /stats
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Получаем статистику пользователя
    stats = await db.get_user_stats(chat_id, user_id)
    
    # Форматирование даты последней активности
    last_active = "Сегодня" if stats["last_active"] is None else stats["last_active"]
    
    # Формируем текст ответа
    response = f"📊 *Ваша статистика активности:*\n\n" \
               f"👤 Пользователь: {message.from_user.full_name}\n" \
               f"💬 Всего сообщений: {stats['total_messages']}\n" \
               f"⭐ Баллы активности: {stats['total_points']:.1f}\n" \
               f"🏆 Ранг: {stats['rank']}\n" \
               f"🕒 Последняя активность: {last_active}"
    
    await message.answer(response, parse_mode=types.ParseMode.MARKDOWN)


# Обработчик команды /top
async def cmd_top(message: types.Message):
    chat_id = message.chat.id
    
    # Получаем список топ-10 активных пользователей
    top_users = await db.get_top_users(chat_id)
    
    if not top_users:
        await message.answer("Пока нет данных об активности в этом чате.")
        return
    
    # Формируем текст ответа
    response = "🏆 <b>Топ активных участников:</b>\n\n"
    
    for i, (user_id, username, first_name, last_name, points, messages) in enumerate(top_users, 1):
        name = username if username else (first_name + (" " + last_name if last_name else ""))
        response += f"{i}. {name} - {points:.1f} баллов ({messages} сообщений)\n"
    
    await message.answer(response, parse_mode=types.ParseMode.HTML)


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
    if user_id not in ADMIN_IDS:
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
    # Если сообщение отправлено в личку боту, игнорируем
    if message.chat.type == types.ChatType.PRIVATE:
        return
    
    logger.debug(f"Обработка обычного сообщения от {message.from_user.id} в чате {message.chat.id}: {message.text}")
    
    # Получаем информацию о пользователе и чате
    user = message.from_user
    chat = message.chat
    
    # Добавляем информацию о чате и пользователе в базу
    await db.add_chat(chat.id, chat.title)
    await db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # Определяем тип сообщения и баллы
    message_type = "reply" if message.reply_to_message else "message"
    points = POINTS_PER_REPLY if message_type == "reply" else POINTS_PER_MESSAGE
    
    # Записываем активность
    await db.add_activity(chat.id, user.id, message_type, points)
    
    
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
    if user_id not in ADMIN_IDS:
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
    if user_id not in ADMIN_IDS:
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
    if user_id not in ADMIN_IDS:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await message.answer("🏆 Определяю самого активного пользователя дня...")
    
    # Запускаем определение и отправку
    from main import bot  # Импортируем бота из main.py
    await send_active_user_of_the_day(bot)
    
    await message.answer("✅ Информация о самом активном пользователе отправлена!")


# Регистрация всех обработчиков
def register_handlers(dp):
    logger.info("Регистрация основных обработчиков")
    try:
        # Регистрация команд - эти обработчики должны иметь ВЫСОКИЙ приоритет
        dp.register_message_handler(cmd_start, Command("start"))
        dp.register_message_handler(cmd_help, Command("help"))
        dp.register_message_handler(cmd_stats, Command("stats"))
        dp.register_message_handler(cmd_top, Command("top"))
        dp.register_message_handler(cmd_challenge, Command("challenge"))
        
        # Добавляем обработчик команды проверки неактивных
        dp.register_message_handler(cmd_check_inactive, Command("check_inactive"))
        
        # Добавляем обработчик команды отправки отчета
        dp.register_message_handler(cmd_send_report, Command("send_report"))
        
        # Добавляем обработчик команды отправки ежедневной темы
        dp.register_message_handler(cmd_send_daily_topic, Command("send_daily_topic"))
        
        # Добавляем обработчик команды активного пользователя
        dp.register_message_handler(cmd_active_user_of_day, Command("active_user_of_day"))
        
        # Регистрация обработчика всех остальных сообщений ПОСЛЕ регистрации команд
        # Регистрируем последним, чтобы обработчик выполнялся последним
        dp.register_message_handler(process_message, content_types=types.ContentTypes.TEXT, state="*")
        
        logger.info("Обработчики успешно зарегистрированы")
    except Exception as e:
        logger.exception(f"Ошибка при регистрации обработчиков: {e}") 