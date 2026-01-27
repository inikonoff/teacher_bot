from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class UserState(StatesGroup):
    subject_selected = State()

SUBJECTS = {
    "math": "Математика 📐",
    "english": "Английский язык 🇬🇧",
    "german": "Немецкий язык 🇩🇪",
    "french": "Французский язык 🇫🇷",
    "russian": "Русский язык 📝",
    "physics": "Физика ⚛️",
    "chemistry": "Химия 🧪",
}

@router.message(Command("start"))
async def cmd_start(message: Message, db):
    user_id = message.from_user.id
    
    # Создаем пользователя если новый
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, message.from_user.username)
    
    # Инлайн кнопки выбора предмета
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=SUBJECTS["math"], callback_data="subject:math"),
            InlineKeyboardButton(text=SUBJECTS["physics"], callback_data="subject:physics")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["chemistry"], callback_data="subject:chemistry"),
            InlineKeyboardButton(text=SUBJECTS["russian"], callback_data="subject:russian")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["english"], callback_data="subject:english"),
            InlineKeyboardButton(text=SUBJECTS["german"], callback_data="subject:german")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["french"], callback_data="subject:french")
        ]
    ])
    
    await message.answer(
        "🎓 Добро пожаловать в бот *Училка*!\n\n"
        "Выберите предмет:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("subject:"))
async def select_subject(callback: CallbackQuery, state: FSMContext, db):
    subject = callback.data.split(":")[1]
    
    await state.update_data(subject=subject)
    await state.set_state(UserState.subject_selected)
    
    await db.update_user_subject(callback.from_user.id, subject)
    
    await callback.message.edit_text(
        f"✅ Выбран предмет: *{SUBJECTS[subject]}*\n\n"
        f"Здравствуйте, садитесь! 👋\n\n"
        f"Я помогу разобраться с темами, но *не решаю задачи за вас*.\n"
        f"Присылайте вопросы текстом или фото заданий.",
        parse_mode="Markdown"
    )

@router.message(Command("change"))
async def cmd_change_subject(message: Message):
    """Сменить предмет"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=SUBJECTS["math"], callback_data="subject:math"),
            InlineKeyboardButton(text=SUBJECTS["physics"], callback_data="subject:physics")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["chemistry"], callback_data="subject:chemistry"),
            InlineKeyboardButton(text=SUBJECTS["russian"], callback_data="subject:russian")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["english"], callback_data="subject:english"),
            InlineKeyboardButton(text=SUBJECTS["german"], callback_data="subject:german")
        ],
        [
            InlineKeyboardButton(text=SUBJECTS["french"], callback_data="subject:french")
        ]
    ])
    
    await message.answer(
        "Выберите новый предмет:",
        reply_markup=keyboard
    )

@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, vision, groq, cache, db):
    user_id = message.from_user.id
    data = await state.get_data()
    subject = data.get('subject')
    
    if not subject:
        await message.answer("Сначала выберите предмет через /start")
        return
    
    # Скачиваем фото
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    image_bytes = await message.bot.download_file(file.file_path)
    
    # Проверка контента (мягкая, без банов)
    is_educational, check_message = await vision.check_content(image_bytes.read())
    
    if not is_educational:
        await message.answer(
            f"😊 {check_message}\n\n"
            "Отправьте фото страницы учебника, тетради или задания, и я помогу разобраться!"
        )
        return
    
    # OCR
    await message.answer("🔍 Распознаю текст с изображения...")
    
    image_bytes.seek(0)
    extracted_text = await vision.extract_text(image_bytes.read())
    
    if "не удалось" in extracted_text.lower():
        await message.answer(extracted_text)
        return
    
    # Показываем распознанный текст
    preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
    await message.answer(
        f"📝 *Распознанный текст:*\n\n{preview}\n\n"
        f"Обрабатываю...",
        parse_mode="Markdown"
    )
    
    # Обработка как текстовый вопрос
    await process_question(message, extracted_text, subject, groq, cache, db)

@router.message(F.text)
async def handle_text(message: Message, state: FSMContext, groq, cache, db):
    user_id = message.from_user.id
    data = await state.get_data()
    subject = data.get('subject')
    
    if not subject:
        await message.answer("Выберите предмет через /start")
        return
    
    await process_question(message, message.text, subject, groq, cache, db)

async def process_question(message, question: str, subject: str, groq, cache, db):
    """Основная логика обработки вопроса"""
    
    # Проверка кеша
    cached = await cache.get(subject, question)
    if cached:
        await message.answer(f"📚 {cached}")
        await db.log_question(message.from_user.id, subject, question, from_cache=True)
        return
    
    # Запрос к Groq
    from prompts import get_system_prompt
    
    messages = [
        {"role": "system", "content": get_system_prompt(subject)},
        {"role": "user", "content": question}
    ]
    
    try:
        response = await groq.get_response(messages)
        
        # Сохранение в кеш
        await cache.set(subject, question, response)
        
        # Логируем вопрос
        await db.log_question(message.from_user.id, subject, question, from_cache=False)
        
        await message.answer(f"📚 {response}")
        
    except Exception as e:
        await message.answer(
            "😔 Извините, произошла временная ошибка.\n\n"
            "Попробуйте:\n"
            "• Переформулировать вопрос\n"
            "• Подождать минуту\n"
            "• Написать вопрос покороче"
        )
        print(f"Error processing question: {e}")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь по боту"""
    await message.answer(
        "🎓 *Как пользоваться ботом Училка:*\n\n"
        "1️⃣ Выберите предмет через /start\n"
        "2️⃣ Отправьте вопрос текстом или фото задания\n"
        "3️⃣ Получите объяснение (но не готовое решение!)\n\n"
        "*Команды:*\n"
        "/start - выбрать предмет\n"
        "/change - сменить предмет\n"
        "/help - эта справка\n\n"
        "💡 *Важно:* Я не решаю задачи за вас, а учу их решать!",
        parse_mode="Markdown"
    )

# ====== АДМИН КОМАНДЫ ======

@router.message(Command("admin"))
async def cmd_admin_menu(message: Message):
    """Меню админки"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    text = """🎛 *Админ-панель бота Училка*

Доступные команды:

📊 *Статистика:*
/stats - общая статистика
/stats_today - статистика за сегодня
/stats_week - статистика за неделю

👥 *Пользователи:*
/top_users - топ активных пользователей

💾 *Кеш:*
/cache_stats - статистика кеша
/clear_cache - очистить старый кеш (>30 дней)

🔧 *Система:*
/health - проверка здоровья бота"""
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("stats"))
async def cmd_stats(message: Message, db):
    """Статистика использования"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("У вас нет доступа к статистике.")
        return
    
    stats = await db.get_stats()
    subject_stats = await db.get_subject_stats()
    
    text = "📊 *Статистика бота Училка*\n\n"
    text += f"👥 Всего пользователей: {stats['total_users']}\n"
    text += f"❓ Всего вопросов: {stats['total_questions']}\n"
    text += f"💾 Из кеша: {stats['cache_hits']} ({stats['cache_hit_rate']:.1f}%)\n\n"
    text += "*Популярность предметов:*\n"
    
    for subj in subject_stats:
        emoji = SUBJECTS.get(subj['subject'], '📚').split()[1] if subj['subject'] in SUBJECTS else '📚'
        name = SUBJECTS.get(subj['subject'], subj['subject']).split()[0]
        text += f"{emoji} {name}: {subj['count']} вопросов\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("stats_today"))
async def cmd_stats_today(message: Message, db):
    """Статистика за сегодня"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    stats = await db.get_stats_today()
    
    text = "📊 *Статистика за сегодня*\n\n"
    text += f"👥 Новых пользователей: {stats['new_users']}\n"
    text += f"❓ Вопросов: {stats['questions_today']}\n"
    text += f"🔥 Активных пользователей: {stats['active_users']}\n"
    text += f"💾 Использование кеша: {stats['cache_hit_rate']:.1f}%\n\n"
    
    if stats['top_subjects']:
        text += "*Топ предметов сегодня:*\n"
        for subj in stats['top_subjects'][:3]:
            emoji = SUBJECTS.get(subj['subject'], '📚').split()[1] if subj['subject'] in SUBJECTS else '📚'
            text += f"{emoji} {subj['subject']}: {subj['count']}\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("stats_week"))
async def cmd_stats_week(message: Message, db):
    """Статистика за неделю"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    stats = await db.get_stats_week()
    
    text = "📊 *Статистика за неделю*\n\n"
    text += f"👥 Новых пользователей: {stats['new_users']}\n"
    text += f"❓ Вопросов: {stats['questions_week']}\n"
    text += f"🔥 Активных пользователей: {stats['active_users']}\n"
    text += f"📈 Средний прирост: {stats['avg_daily_questions']:.1f} вопросов/день\n\n"
    
    text += "*Динамика по дням:*\n"
    for day in stats['daily_breakdown']:
        text += f"• {day['date']}: {day['count']} вопросов\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("top_users"))
async def cmd_top_users(message: Message, db):
    """Топ активных пользователей"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    top_users = await db.get_top_users(limit=10)
    
    text = "👑 *Топ-10 активных пользователей*\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for idx, user in enumerate(top_users):
        medal = medals[idx] if idx < 3 else f"{idx + 1}."
        username = user['username'] or f"user_{user['user_id']}"
        text += f"{medal} @{username}: {user['question_count']} вопросов\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("cache_stats"))
async def cmd_cache_stats(message: Message, db):
    """Статистика кеша"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    cache_stats = await db.get_cache_stats()
    
    text = "💾 *Статистика кеша*\n\n"
    text += f"📦 Записей в кеше: {cache_stats['total_cached']}\n"
    text += f"🔥 Самый популярный предмет: {cache_stats['most_cached_subject']}\n"
    text += f"⭐️ Средние хиты: {cache_stats['avg_hits']:.1f}\n\n"
    
    text += "*Топ-5 популярных вопросов:*\n"
    for idx, item in enumerate(cache_stats['top_cached'][:5], 1):
        question = item['question'][:50] + "..." if len(item['question']) > 50 else item['question']
        text += f"{idx}. {question} ({item['hit_count']} хитов)\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("health"))
async def cmd_health(message: Message, db, groq):
    """Проверка здоровья системы"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    text = "🏥 *Проверка системы*\n\n"
    
    # Проверка БД
    try:
        await db.get_stats()
        text += "✅ База данных: OK\n"
    except Exception as e:
        text += f"❌ База данных: ОШИБКА ({str(e)[:50]})\n"
    
    # Проверка Groq API
    try:
        test_response = await groq.get_response([
            {"role": "user", "content": "Привет, это тест. Ответь одним словом: OK"}
        ])
        text += "✅ Groq API: OK\n"
    except Exception as e:
        text += f"❌ Groq API: ОШИБКА ({str(e)[:50]})\n"
    
    # Количество API ключей
    text += f"\n🔑 API ключей: {len(config.GROQ_API_KEYS)}\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("clear_cache"))
async def cmd_clear_cache(message: Message, db):
    """Очистить старый кеш"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    deleted = await db.clear_old_cache(days=30)
    
    await message.answer(
        f"🧹 Очищен кеш старше 30 дней\n\n"
        f"Удалено записей: {deleted}",
        parse_mode="Markdown"
    )
