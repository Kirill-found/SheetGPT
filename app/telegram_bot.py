"""
SheetGPT Telegram Bot v1.0.0

Telegram бот для работы с SheetGPT API.
Позволяет отправлять Excel/CSV файлы и получать анализ данных.
"""

import asyncio
import logging
import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import httpx

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API URL (внутренний вызов)
API_URL = os.getenv("SHEETGPT_API_URL", "http://localhost:8000")

# Хранилище данных пользователей (в памяти для MVP)
user_data_store = {}


class SheetGPTBot:
    """Telegram бот для SheetGPT"""

    def __init__(self, token: str, admin_id: int):
        self.token = token
        self.admin_id = admin_id
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started bot")

        welcome_text = f"""
Привет, {user.first_name}!

Я SheetGPT Bot - твой AI-помощник для работы с таблицами.

**Что я умею:**
- Анализировать Excel/CSV файлы
- Генерировать формулы
- Находить данные по условиям
- Создавать сводки и отчёты

**Как использовать:**
1. Отправь мне Excel (.xlsx) или CSV файл
2. Задай вопрос по данным

**Примеры запросов:**
- "Сумма продаж по менеджерам"
- "Топ 5 товаров по выручке"
- "Выдели строки где сумма > 10000"
- "Средняя цена товаров"

**Команды:**
/start - Начать работу
/help - Справка
/status - Статус
/clear - Очистить данные

Загрузи файл, чтобы начать!
"""
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
**Справка по SheetGPT Bot**

**Поддерживаемые форматы:**
- Excel (.xlsx, .xls)
- CSV (.csv)

**Типы запросов:**

**Формулы:**
- "Формула для суммы колонки B"
- "VLOOKUP для поиска цены"

**Анализ:**
- "Сколько всего продаж"
- "Средняя цена по категориям"
- "Топ 10 клиентов"

**Действия:**
- "Выдели строки где цена > 1000"
- "Отфильтруй данные по региону"

**Советы:**
- Первая строка файла должна содержать заголовки
- Указывайте точные названия колонок
- Можно задавать вопросы на русском языке
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        user_id = update.effective_user.id

        # Проверяем, есть ли загруженные данные
        has_data = user_id in user_data_store and user_data_store[user_id].get('df') is not None

        status_text = f"""
**Статус SheetGPT Bot**

**Пользователь:** {update.effective_user.first_name}
**Telegram ID:** {user_id}

**Загруженные данные:** {'Да' if has_data else 'Нет'}
"""
        if has_data:
            df = user_data_store[user_id]['df']
            filename = user_data_store[user_id].get('filename', 'unknown')
            status_text += f"""
**Файл:** {filename}
**Размер:** {len(df)} строк x {len(df.columns)} колонок
**Колонки:** {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}
"""

        status_text += f"""
**Время:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        await update.message.reply_text(status_text, parse_mode='Markdown')

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear - очистить данные"""
        user_id = update.effective_user.id

        if user_id in user_data_store:
            del user_data_store[user_id]
            await update.message.reply_text("Данные очищены. Загрузите новый файл.")
        else:
            await update.message.reply_text("У вас нет загруженных данных.")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка загруженного файла"""
        user_id = update.effective_user.id
        document = update.message.document
        filename = document.file_name.lower()

        # Проверяем формат файла
        if not any(filename.endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
            await update.message.reply_text(
                "Неподдерживаемый формат файла.\n"
                "Поддерживаются: .xlsx, .xls, .csv"
            )
            return

        await update.message.reply_text("Загружаю файл...")

        try:
            # Скачиваем файл
            file = await context.bot.get_file(document.file_id)
            file_bytes = await file.download_as_bytearray()

            # Читаем данные
            if filename.endswith('.csv'):
                # Пробуем разные кодировки
                for encoding in ['utf-8', 'cp1251', 'latin1']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Не удалось определить кодировку CSV файла")
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))

            # Проверяем данные
            if df.empty:
                await update.message.reply_text("Файл пустой или не содержит данных.")
                return

            # Сохраняем данные пользователя
            user_data_store[user_id] = {
                'df': df,
                'filename': document.file_name,
                'uploaded_at': datetime.now()
            }

            # Формируем ответ
            columns_preview = ', '.join(df.columns[:8])
            if len(df.columns) > 8:
                columns_preview += f' и ещё {len(df.columns) - 8}'

            preview_rows = min(3, len(df))
            data_preview = df.head(preview_rows).to_string(index=False, max_colwidth=20)

            response = f"""
**Файл загружен!**

**Файл:** {document.file_name}
**Размер:** {len(df)} строк x {len(df.columns)} колонок

**Колонки:**
{columns_preview}

**Превью данных:**
```
{data_preview}
```

Теперь задай вопрос по данным!
Например: "Сумма по колонке Продажи" или "Топ 5 по выручке"
"""
            await update.message.reply_text(response, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            await update.message.reply_text(
                f"Ошибка обработки файла:\n{str(e)}\n\n"
                "Попробуйте другой файл или формат."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстового сообщения (запроса)"""
        user_id = update.effective_user.id
        query = update.message.text

        # Проверяем, есть ли данные
        if user_id not in user_data_store or user_data_store[user_id].get('df') is None:
            await update.message.reply_text(
                "Сначала загрузите Excel или CSV файл.\n"
                "Просто отправьте файл в этот чат."
            )
            return

        df = user_data_store[user_id]['df']

        await update.message.reply_text("Обрабатываю запрос...")

        try:
            # Подготавливаем данные для API
            column_names = df.columns.tolist()
            sheet_data = df.values.tolist()

            # Вызываем API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{API_URL}/api/v1/formula",
                    json={
                        "query": query,
                        "column_names": column_names,
                        "sheet_data": sheet_data
                    }
                )

                if response.status_code != 200:
                    error_detail = response.json().get('detail', {})
                    user_message = error_detail.get('user_message', 'Ошибка обработки')
                    await update.message.reply_text(f"Ошибка: {user_message}")
                    return

                result = response.json()

            # Формируем ответ
            response_text = self.format_response(result)
            await update.message.reply_text(response_text, parse_mode='Markdown')

        except httpx.TimeoutException:
            await update.message.reply_text(
                "Превышено время ожидания.\n"
                "Попробуйте упростить запрос или уменьшить объём данных."
            )
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            await update.message.reply_text(
                f"Ошибка обработки:\n{str(e)}"
            )

    def format_response(self, result: dict) -> str:
        """Форматирование ответа API для Telegram"""
        parts = []

        # Summary (основной результат)
        if result.get('summary'):
            parts.append(f"**Результат:**\n{result['summary']}")

        # Формула
        if result.get('formula'):
            parts.append(f"**Формула:**\n`{result['formula']}`")

        # Explanation
        if result.get('explanation'):
            parts.append(f"**Пояснение:**\n{result['explanation']}")

        # Key findings
        if result.get('key_findings'):
            findings = '\n'.join(f"- {f}" for f in result['key_findings'][:5])
            parts.append(f"**Ключевые находки:**\n{findings}")

        # Methodology
        if result.get('methodology'):
            parts.append(f"**Методология:**\n{result['methodology']}")

        # Highlighting info
        if result.get('highlight_rows'):
            rows = result['highlight_rows']
            color = result.get('highlight_color', 'yellow')
            parts.append(f"**Подсветка:** {len(rows)} строк ({color})")

        # Structured data (таблицы)
        if result.get('structured_data'):
            data = result['structured_data']
            if data.get('rows') and len(data['rows']) <= 10:
                table_preview = self.format_table(data)
                parts.append(f"**Данные:**\n```\n{table_preview}\n```")

        # Function used (для отладки)
        if result.get('function_used'):
            parts.append(f"_Функция: {result['function_used']}_")

        return '\n\n'.join(parts) if parts else "Запрос обработан"

    def format_table(self, structured_data: dict) -> str:
        """Форматирование таблицы для Telegram"""
        headers = structured_data.get('headers', [])
        rows = structured_data.get('rows', [])

        if not headers or not rows:
            return "Нет данных"

        # Ограничиваем ширину колонок
        max_col_width = 15

        # Форматируем заголовки
        header_line = ' | '.join(str(h)[:max_col_width].ljust(max_col_width) for h in headers)
        separator = '-' * len(header_line)

        # Форматируем строки
        row_lines = []
        for row in rows[:10]:  # Максимум 10 строк
            row_str = ' | '.join(str(cell)[:max_col_width].ljust(max_col_width) for cell in row)
            row_lines.append(row_str)

        return f"{header_line}\n{separator}\n" + '\n'.join(row_lines)

    async def admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /broadcast - рассылка (только для админа)"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("Эта команда доступна только администратору.")
            return

        if not context.args:
            await update.message.reply_text("Использование: /broadcast <сообщение>")
            return

        message = ' '.join(context.args)
        await update.message.reply_text(f"Рассылка (MVP - только лог):\n{message}")

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика (только для админа)"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("Эта команда доступна только администратору.")
            return

        active_users = len(user_data_store)
        stats_text = f"""
**Статистика бота**

Активных сессий: {active_users}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    def run(self):
        """Запуск бота"""
        logger.info("Starting SheetGPT Telegram Bot...")

        # Создаем приложение
        self.application = Application.builder().token(self.token).build()

        # Регистрируем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("broadcast", self.admin_broadcast))
        self.application.add_handler(CommandHandler("stats", self.admin_stats))

        # Обработчик файлов
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))

        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Запускаем бота
        logger.info("Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Точка входа"""
    from app.core.config import settings

    token = settings.TELEGRAM_BOT_TOKEN
    admin_id = settings.TELEGRAM_ADMIN_ID

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    if not admin_id:
        logger.warning("TELEGRAM_ADMIN_ID not set - admin commands will be disabled")

    bot = SheetGPTBot(token=token, admin_id=admin_id)
    bot.run()


if __name__ == "__main__":
    main()
