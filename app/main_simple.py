"""
Упрощенная версия для быстрого теста (без БД)
+ Telegram Bot в фоновом потоке
"""
import threading
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import formula

logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered assistant for Google Sheets",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS для Apps Script
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для теста разрешаем всё
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(formula.router)


def start_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        from app.telegram_bot import SheetGPTBot

        token = settings.TELEGRAM_BOT_TOKEN
        admin_id = settings.TELEGRAM_ADMIN_ID

        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not set - bot disabled")
            return

        database_url = settings.DATABASE_URL
        logger.info(f"Starting Telegram bot (admin_id: {admin_id})")
        bot = SheetGPTBot(token=token, admin_id=admin_id, database_url=database_url)
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")




def start_admin_bot():
    """Запуск Admin бота в отдельном потоке"""
    import traceback
    logger.info("=== ADMIN BOT THREAD STARTED ===")
    try:
        from app.admin_bot import SheetGPTAdminBot
        logger.info("Admin bot import OK")

        admin_token = "8472527828:AAHXB30EtficnooQnNsOLrJqhoE6yotSZaE"
        main_token = settings.TELEGRAM_BOT_TOKEN
        database_url = settings.DATABASE_URL

        if not main_token:
            logger.warning("Main bot token not set - admin bot disabled")
            return

        if not database_url:
            logger.warning("DATABASE_URL not set - admin bot disabled")
            return

        logger.info("Starting Admin bot...")
        bot = SheetGPTAdminBot(
            token=admin_token,
            main_bot_token=main_token,
            database_url=database_url
        )
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start Admin bot: {e}")
        logger.error(traceback.format_exc())

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Server running (without DB for quick start)")

    # Запускаем Telegram бота в отдельном потоке
    if settings.TELEGRAM_BOT_TOKEN:
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        print("Telegram bot started in background thread")
    else:
        print("Telegram bot disabled (no token)")
    # Запускаем Admin бота в отдельном потоке
    logger.info(f"DEBUG: TELEGRAM_BOT_TOKEN set: {bool(settings.TELEGRAM_BOT_TOKEN)}")
    logger.info(f"DEBUG: DATABASE_URL set: {bool(settings.DATABASE_URL)}")
    logger.info(f"DEBUG: DATABASE_URL value: {settings.DATABASE_URL[:30] if settings.DATABASE_URL else 'EMPTY'}...")
    if settings.TELEGRAM_BOT_TOKEN and settings.DATABASE_URL:
        admin_thread = threading.Thread(target=start_admin_bot, daemon=True)
        admin_thread.start()
        print("Admin bot started in background thread")
    else:
        logger.info("Admin bot DISABLED - missing token or database_url")



@app.get("/", tags=["root"])
async def root():
    """Корневой эндпоинт"""
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check для мониторинга"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "gemini_configured": settings.GEMINI_API_KEY != "your-gemini-api-key-here",
        "telegram_bot_enabled": bool(settings.TELEGRAM_BOT_TOKEN)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
