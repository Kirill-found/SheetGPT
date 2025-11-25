#!/usr/bin/env python3
"""
Запуск Telegram бота SheetGPT

Запуск: python run_bot.py

Необходимые переменные окружения:
- TELEGRAM_BOT_TOKEN: токен от @BotFather
- TELEGRAM_ADMIN_ID: твой Telegram ID для админских команд
"""

import os
import sys

from dotenv import load_dotenv
load_dotenv()

from app.telegram_bot import main

if __name__ == "__main__":
    main()
