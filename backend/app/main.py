from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import formula, actions
# v1.1.0: Added conversation_id support for contextual queries

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.1.0-PANDAS-AGG",  # v2.1.0: Real Python pandas aggregation
    description="AI-powered assistant for Google Sheets with conversation memory",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS для Apps Script
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем роутеры
app.include_router(formula.router)
app.include_router(actions.router)  # Interactive Builder API


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"📝 Environment: {settings.ENVIRONMENT}")

    # Инициализируем базу данных
    try:
        await init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database init warning: {e}")


@app.get("/", tags=["root"])
async def root():
    """Корневой эндпоинт"""
    return {
        "app": settings.PROJECT_NAME,
        "version": "2.1.0-PANDAS-AGG",
        "status": "running",
        "features": ["conversation_history", "english_formulas", "interactive_builder"],
        "docs": "/docs"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check для мониторинга"""
    return {
        "status": "healthy",
        "version": "2.1.0-PANDAS-AGG",
        "environment": settings.ENVIRONMENT,
        "features": ["conversation_history", "english_formulas"]
    }


@app.get("/debug/build-info", tags=["debug"])
async def build_info():
    """Debug endpoint для проверки какой код задеплоен"""
    import os
    return {
        "version": "2.0.0",
        "build_date": "2025-11-09-v2.0.0-gemini-migration",
        "dockerfile_cmd": "app.main:app (NOT app.main_simple:app)",
        "features": ["conversation_history", "english_formulas", "interactive_builder"],
        "railway_deployed": True,
        "env": settings.ENVIRONMENT,
        "build_marker": "GEMINI_MIGRATION_bb63273"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )
