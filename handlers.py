# handlers.py - добавить в конец файла

from datetime import datetime, timedelta

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
        emoji = SUBJECTS.get(subj['subject'], '📚').split()[1]
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
            emoji = SUBJECTS.get(subj['subject'], '📚').split()[1]
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
/health - проверка здоровья бота
/broadcast - разослать сообщение всем (осторожно!)"""
    
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

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Начать рассылку"""
    from config import Config
    config = Config()
    
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # Здесь можно добавить FSM для ввода текста рассылки
    await message.answer(
        "⚠️ *Рассылка временно отключена*\n\n"
        "Для рассылки свяжитесь с разработчиком.",
        parse_mode="Markdown"
    )
