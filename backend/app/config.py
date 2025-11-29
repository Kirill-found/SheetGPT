"""
Configuration settings for SheetGPT API
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Environment
    environment: str = "development"

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    gemini_api_key: str = ""

    # Database settings
    DATABASE_URL: str = "postgresql://user:pass@localhost/sheetgpt"

    # JWT Security
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 43200

    # CORS
    cors_origins: str = '["http://localhost:3000"]'

    # Rate limits
    free_tier_queries_limit: int = 20
    starter_tier_queries_limit: int = 200
    pro_tier_queries_limit: int = 1000

    # App settings
    APP_NAME: str = "SheetGPT API"
    APP_VERSION: str = "6.2.8"
    DEBUG: bool = False

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_ID: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env

settings = Settings()