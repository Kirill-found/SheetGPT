"""
Configuration settings for SheetGPT API
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/sheetgpt")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

    # App settings
    APP_NAME: str = "SheetGPT API"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()