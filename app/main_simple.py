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

        logger.info(f"Starting Telegram bot (admin_id: {admin_id})")
        bot = SheetGPTBot(token=token, admin_id=admin_id)
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")


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
