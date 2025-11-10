"""
Упрощенная версия для быстрого теста (без БД)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import formula

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


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Server running (without DB for quick start)")


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
        "gemini_configured": settings.GEMINI_API_KEY != "your-gemini-api-key-here"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
