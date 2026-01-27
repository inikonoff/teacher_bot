import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiohttp import web

from config import Config
from handlers import router
from groq_client import GroqRouter
from vision import VisionProcessor
from cache import Cache
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Endpoint для UptimeRobot - держит Render живым"""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Мини-сервер для UptimeRobot"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logger.info("Health server started on port 8000")

async def main():
    config = Config()
    
    # Инициализация компонентов
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Groq с rotation API ключей
    groq_router = GroqRouter(config.GROQ_API_KEYS)
    vision = VisionProcessor(groq_router)
    cache = Cache(config.SUPABASE_URL, config.SUPABASE_KEY)
    db = Database(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    # Middleware для внедрения зависимостей
    @dp.message.middleware()
    async def inject_dependencies(handler, event, data):
        data['groq'] = groq_router
        data['vision'] = vision
        data['cache'] = cache
        data['db'] = db
        return await handler(event, data)
    
    @dp.callback_query.middleware()
    async def inject_dependencies_callback(handler, event, data):
        data['groq'] = groq_router
        data['vision'] = vision
        data['cache'] = cache
        data['db'] = db
        return await handler(event, data)
    
    dp.include_router(router)
    
    # Запускаем health-сервер и polling параллельно
    logger.info("Starting bot...")
    
    await asyncio.gather(
        start_health_server(),
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
