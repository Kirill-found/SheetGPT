from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Настройки приложения из .env файла"""

    # Окружение
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "SheetGPT"
    VERSION: str = "1.0.0"

    # База данных
    DATABASE_URL: str

    # AI API ключи
    OPENAI_API_KEY: str  # GPT-4o for production

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 43200  # 30 дней

    # CORS
    CORS_ORIGINS: List[str] = [
        "https://script.google.com",
        "https://docs.google.com"
    ]

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Rate limiting
    FREE_TIER_QUERIES_LIMIT: int = 20
    STARTER_TIER_QUERIES_LIMIT: int = 200
    PRO_TIER_QUERIES_LIMIT: int = 1000

    # AI модели (GPT-4o production)
    FORMULA_MODEL: str = "gpt-4o"
    ANALYSIS_MODEL: str = "gpt-4o"
    REPORT_MODEL: str = "gpt-4o"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Синглтон настроек
settings = Settings()
