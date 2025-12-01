"""
SheetGPT Telegram Bot v2.0.0

Telegram бот с интерактивным меню для SheetGPT.
"""

import logging
import os
import io
import asyncio
import secrets
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
    ConversationHandler,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище данных (в памяти для MVP)
user_data_store = {}
user_reviews = []   # [{user_id, username, rating, text, date}] - TODO: переместить в БД

# Состояния для ConversationHandler
WAITING_REVIEW_RATING, WAITING_REVIEW_TEXT, WAITING_SUPPORT_MESSAGE = range(3)

# Ссылки (можно вынести в config)
CHROME_EXTENSION_URL = "https://chrome.google.com/webstore/detail/sheetgpt"  # TODO: заменить на реальную
INSTALLATION_GUIDE_URL = "https://docs.google.com/document/d/YOUR_DOC_ID"  # TODO: заменить на реальную
SUPPORT_CHAT_URL = "https://t.me/sheetgpt_support"  # TODO: создать чат поддержки


class SheetGPTBot:
    """Telegram бот для SheetGPT"""

    def __init__(self, token: str, admin_id: int, database_url: str = None):
        self.token = token
        self.admin_id = admin_id
        self.application = None
        self.database_url = database_url
        self.async_engine = None
        self.async_session_factory = None

    def _init_db(self):
        """Инициализация подключения к БД"""
        if self.database_url:
            # Конвертируем postgres:// в postgresql+asyncpg://
            db_url = self.database_url
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://") and "asyncpg" not in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self.async_engine = create_async_engine(db_url, echo=False)
            self.async_session_factory = sessionmaker(
                self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("Database connection initialized for bot")

    def get_main_menu_keyboard(self):
        """Создание главного меню с кнопками"""
        keyboard = [
            [InlineKeyboardButton("🌐 Chrome Extension", callback_data="menu_extension")],
            [InlineKeyboardButton("📖 Инструкция по установке", callback_data="menu_guide")],
            [InlineKeyboardButton("🔑 Лицензионный ключ", callback_data="menu_license")],
            [InlineKeyboardButton("💳 Подписка", callback_data="menu_subscription")],
            [InlineKeyboardButton("🆘 Поддержка", callback_data="menu_support")],
            [InlineKeyboardButton("⭐ Отзывы", callback_data="menu_reviews")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_back_button(self):
        """Кнопка возврата в главное меню"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
        ])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - показываем главное меню"""
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started bot")

        welcome_text = f"""
Привет, {user.first_name}! 👋

Добро пожаловать в **SheetGPT Bot** - твой AI-помощник для работы с Google Sheets.

Выбери нужный раздел:
"""
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=self.get_main_menu_keyboard()
        )

    async def menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки меню"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "menu_back":
            await self.show_main_menu(query)
        elif data == "menu_extension":
            await self.show_extension(query)
        elif data == "menu_guide":
            await self.show_guide(query)
        elif data == "menu_license":
            await self.show_license(query, context)
        elif data == "menu_subscription":
            await self.show_subscription(query)
        elif data == "menu_support":
            await self.show_support(query)
        elif data == "menu_reviews":
            await self.show_reviews(query)
        elif data == "license_generate":
            await self.generate_license(query, context)
        elif data == "license_show":
            await self.show_my_license(query)
        elif data == "sub_plans":
            await self.show_subscription_plans(query)
        elif data == "sub_cancel":
            await self.cancel_subscription(query)
        elif data == "reviews_add":
            await self.start_review(query, context)
        elif data == "reviews_view":
            await self.view_reviews(query)
        elif data.startswith("rating_"):
            await self.save_rating(query, context, data)

    async def show_main_menu(self, query):
        """Показать главное меню"""
        text = """
**SheetGPT Bot** - Главное меню

Выбери нужный раздел:
"""
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=self.get_main_menu_keyboard()
        )

    async def show_extension(self, query):
        """Раздел Chrome Extension"""
        text = f"""
🌐 **Chrome Extension**

SheetGPT работает как расширение для Google Chrome, которое интегрируется напрямую в Google Sheets.

**Возможности:**
• AI-анализ данных прямо в таблице
• Генерация формул на естественном языке
• Автоматическая подсветка данных
• Создание графиков и отчётов

👇 Нажми кнопку ниже для установки:
"""
        keyboard = [
            [InlineKeyboardButton("📥 Установить расширение", url=CHROME_EXTENSION_URL)],
            [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_guide(self, query):
        """Раздел Инструкция по установке"""
        text = f"""
📖 **Инструкция по установке**

Подробная инструкция по установке и настройке SheetGPT.

**Содержание:**
1. Установка Chrome Extension
2. Активация лицензии
3. Первый запуск
4. Основные функции
5. Часто задаваемые вопросы

👇 Открой инструкцию:
"""
        keyboard = [
            [InlineKeyboardButton("📄 Открыть инструкцию", url=INSTALLATION_GUIDE_URL)],
            [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_license(self, query, context):
        """Раздел Лицензионный ключ - проверяем напрямую в БД"""
        user_id = query.from_user.id
        has_license = False

        if self.async_session_factory:
            try:
                from app.models.telegram_user import TelegramUser
                async with self.async_session_factory() as session:
                    result = await session.execute(
                        select(TelegramUser).where(TelegramUser.telegram_user_id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    has_license = user and user.license_key
            except Exception as e:
                logger.error(f"Error checking license: {e}")

        if has_license:
            text = f"""
🔑 **Лицензионный ключ**

✅ У тебя уже есть лицензионный ключ!

Выбери действие:
"""
            keyboard = [
                [InlineKeyboardButton("👁 Показать мой ключ", callback_data="license_show")],
                [InlineKeyboardButton("🔄 Сгенерировать новый", callback_data="license_generate")],
                [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
            ]
        else:
            text = f"""
🔑 **Лицензионный ключ**

У тебя пока нет лицензионного ключа.

Сгенерируй ключ для активации SheetGPT:
"""
            keyboard = [
                [InlineKeyboardButton("🔐 Сгенерировать ключ", callback_data="license_generate")],
                [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
            ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def generate_license(self, query, context):
        """Генерация лицензионного ключа напрямую в БД"""
        user = query.from_user
        user_id = user.id
        text = "❌ База данных не настроена"

        if self.async_session_factory:
            try:
                from app.models.telegram_user import TelegramUser
                async with self.async_session_factory() as session:
                    # Ищем пользователя
                    result = await session.execute(
                        select(TelegramUser).where(TelegramUser.telegram_user_id == user_id)
                    )
                    db_user = result.scalar_one_or_none()

                    if db_user:
                        # Генерируем новый ключ
                        license_key = TelegramUser.generate_license_key()
                        db_user.license_key = license_key
                    else:
                        # Создаём нового пользователя с ключом
                        license_key = TelegramUser.generate_license_key()
                        db_user = TelegramUser(
                            telegram_user_id=user_id,
                            username=user.username,
                            first_name=user.first_name,
                            license_key=license_key,
                            api_token=TelegramUser.generate_api_token()
                        )
                        session.add(db_user)

                    await session.commit()

                    text = f"""
🔑 **Твой лицензионный ключ**

```
{license_key}
```

📋 Скопируй этот ключ и вставь в настройках расширения SheetGPT.

⚠️ Не передавай ключ третьим лицам!
"""
            except Exception as e:
                logger.error(f"Error generating license: {e}")
                text = f"❌ Ошибка: {str(e)}"

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=self.get_back_button()
        )

    async def show_my_license(self, query):
        """Показать текущий ключ и статистику использования"""
        user_id = query.from_user.id
        text = "❌ База данных не настроена"

        if self.async_session_factory:
            try:
                from app.models.telegram_user import TelegramUser
                async with self.async_session_factory() as session:
                    result = await session.execute(
                        select(TelegramUser).where(TelegramUser.telegram_user_id == user_id)
                    )
                    db_user = result.scalar_one_or_none()

                    if db_user and db_user.license_key:
                        license_key = db_user.license_key
                        tier = db_user.subscription_tier or 'free'
                        queries_used = db_user.queries_used_today or 0
                        queries_limit = db_user.queries_limit or 10
                        total_queries = db_user.total_queries or 0

                        # Создаём прогресс-бар
                        if tier == 'premium':
                            usage_info = "∞ Безлимит"
                        else:
                            progress = min(queries_used / queries_limit, 1.0) if queries_limit > 0 else 0
                            filled = int(progress * 10)
                            bar = '█' * filled + '░' * (10 - filled)
                            remaining = max(0, queries_limit - queries_used)
                            usage_info = f"`[{bar}]` {queries_used}/{queries_limit}\n📈 Осталось: **{remaining}**"

                        text = f"""
🔑 **Твой лицензионный ключ**

```
{license_key}
```

📊 **Тариф:** {tier.capitalize()}
✅ **Статус:** Активен

**Использование сегодня:**
{usage_info}

📊 Всего запросов: {total_queries}
"""
                    else:
                        text = "❌ У тебя нет лицензионного ключа. Нажми 'Сгенерировать ключ'."

            except Exception as e:
                logger.error(f"Error getting license: {e}")
                text = f"❌ Ошибка: {str(e)}"

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=self.get_back_button()
        )

    async def show_subscription(self, query):
        """Раздел Подписка - показывает реальные данные из БД"""
        user_id = query.from_user.id

        # Получаем данные из БД
        subscription_tier = "free"
        queries_used = 0
        queries_limit = 10
        total_queries = 0
        premium_until = None

        if self.async_session_factory:
            try:
                from app.models.telegram_user import TelegramUser
                async with self.async_session_factory() as session:
                    result = await session.execute(
                        select(TelegramUser).where(TelegramUser.telegram_user_id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        subscription_tier = user.subscription_tier or "free"
                        queries_used = user.queries_used_today or 0
                        queries_limit = user.queries_limit or 10
                        total_queries = user.total_queries or 0
                        premium_until = user.premium_until
            except Exception as e:
                logger.error(f"Error getting subscription: {e}")

        is_premium = subscription_tier == "premium"

        if is_premium:
            premium_date = premium_until.strftime('%d.%m.%Y') if premium_until else 'Бессрочно'
            text = f"""
💳 **Подписка**

✅ У тебя активная подписка **Premium**

📅 Действует до: {premium_date}
📊 Всего запросов: {total_queries}

Что включено:
• ∞ Безлимитные запросы
• Приоритетная поддержка
• Все будущие обновления
"""
            keyboard = [
                [InlineKeyboardButton("❌ Отменить подписку", callback_data="sub_cancel")],
                [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
            ]
        else:
            # Создаём прогресс-бар
            progress = min(queries_used / queries_limit, 1.0) if queries_limit > 0 else 0
            filled = int(progress * 10)
            bar = '█' * filled + '░' * (10 - filled)
            remaining = max(0, queries_limit - queries_used)

            text = f"""
💳 **Подписка**

📊 **Тариф:** Free

**Использование сегодня:**
`[{bar}]` {queries_used}/{queries_limit}

📈 Осталось запросов: **{remaining}**
📊 Всего запросов: {total_queries}

Хочешь больше? Переходи на Premium!
"""
            keyboard = [
                [InlineKeyboardButton("⭐ Получить Unlimited", callback_data="sub_plans")],
                [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
            ]

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_subscription_plans(self, query):
        """Показать тарифные планы"""
        text = """
💳 **Тарифные планы**

**🆓 Free** - Бесплатно
• 10 запросов в день
• Базовые формулы
• Email поддержка

**⭐ Starter** - $9/месяц
• 200 запросов в день
• Все типы анализа
• Приоритетная поддержка

**🚀 Pro** - $29/месяц
• Безлимитные запросы
• API доступ
• Персональный менеджер

👇 Для оплаты напиши в поддержку:
"""
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", url=SUPPORT_CHAT_URL)],
            [InlineKeyboardButton("« Назад", callback_data="menu_subscription")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def cancel_subscription(self, query):
        """Отмена подписки"""
        text = """
❌ **Отмена подписки**

Ты уверен, что хочешь отменить подписку?

После отмены:
• Подписка будет активна до конца оплаченного периода
• Затем аккаунт перейдёт на бесплатный план

Для отмены напиши в поддержку.
"""
        keyboard = [
            [InlineKeyboardButton("💬 Написать в поддержку", url=SUPPORT_CHAT_URL)],
            [InlineKeyboardButton("« Назад", callback_data="menu_subscription")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_support(self, query):
        """Раздел Поддержка"""
        text = f"""
🆘 **Поддержка**

Нужна помощь? Мы всегда на связи!

**Способы связи:**

💬 **Чат поддержки** - для быстрых вопросов
📧 **Email:** support@sheetgpt.ai
📚 **FAQ** - в инструкции по установке

**Время ответа:**
• Чат: до 2 часов
• Email: до 24 часов

👇 Выбери способ связи:
"""
        keyboard = [
            [InlineKeyboardButton("💬 Открыть чат поддержки", url=SUPPORT_CHAT_URL)],
            [InlineKeyboardButton("📖 Читать FAQ", url=INSTALLATION_GUIDE_URL)],
            [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_reviews(self, query):
        """Раздел Отзывы"""
        # Считаем среднюю оценку
        if user_reviews:
            avg_rating = sum(r['rating'] for r in user_reviews) / len(user_reviews)
            rating_stars = '⭐' * round(avg_rating)
            stats = f"Средняя оценка: {rating_stars} ({avg_rating:.1f}/5)\nВсего отзывов: {len(user_reviews)}"
        else:
            stats = "Пока нет отзывов. Будь первым!"

        text = f"""
⭐ **Отзывы**

{stats}

Поделись своим мнением о SheetGPT!
"""
        keyboard = [
            [InlineKeyboardButton("✍️ Оставить отзыв", callback_data="reviews_add")],
            [InlineKeyboardButton("👀 Посмотреть отзывы", callback_data="reviews_view")],
            [InlineKeyboardButton("« Назад в меню", callback_data="menu_back")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_review(self, query, context):
        """Начать оставление отзыва - выбор оценки"""
        text = """
✍️ **Оставить отзыв**

Выбери оценку:
"""
        keyboard = [
            [
                InlineKeyboardButton("1 ⭐", callback_data="rating_1"),
                InlineKeyboardButton("2 ⭐", callback_data="rating_2"),
                InlineKeyboardButton("3 ⭐", callback_data="rating_3"),
                InlineKeyboardButton("4 ⭐", callback_data="rating_4"),
                InlineKeyboardButton("5 ⭐", callback_data="rating_5"),
            ],
            [InlineKeyboardButton("« Отмена", callback_data="menu_reviews")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def save_rating(self, query, context, data):
        """Сохранить оценку и попросить текст отзыва"""
        rating = int(data.split('_')[1])
        context.user_data['pending_rating'] = rating

        text = f"""
✍️ **Оставить отзыв**

Твоя оценка: {'⭐' * rating}

Теперь напиши текст отзыва (или отправь /skip чтобы пропустить):
"""
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['waiting_review_text'] = True

    async def handle_review_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текста отзыва"""
        if not context.user_data.get('waiting_review_text'):
            return False

        user = update.effective_user
        rating = context.user_data.get('pending_rating', 5)
        text = update.message.text

        if text == '/skip':
            text = ''

        # Сохраняем отзыв
        review = {
            'user_id': user.id,
            'username': user.username or user.first_name,
            'rating': rating,
            'text': text,
            'date': datetime.now()
        }
        user_reviews.append(review)

        # Очищаем состояние
        context.user_data.pop('waiting_review_text', None)
        context.user_data.pop('pending_rating', None)

        await update.message.reply_text(
            f"✅ Спасибо за отзыв!\n\nТвоя оценка: {'⭐' * rating}",
            reply_markup=self.get_back_button()
        )
        return True

    async def view_reviews(self, query):
        """Посмотреть отзывы"""
        if not user_reviews:
            text = "📭 Пока нет отзывов."
        else:
            # Показываем последние 5 отзывов
            text = "👀 **Последние отзывы:**\n\n"
            for review in user_reviews[-5:]:
                stars = '⭐' * review['rating']
                username = review['username'][:15]
                date = review['date'].strftime('%d.%m.%Y')
                review_text = review['text'][:100] + '...' if len(review['text']) > 100 else review['text']

                text += f"**{username}** {stars}\n"
                if review_text:
                    text += f"_{review_text}_\n"
                text += f"📅 {date}\n\n"

        keyboard = [
            [InlineKeyboardButton("« Назад", callback_data="menu_reviews")]
        ]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        # Сначала проверяем, ждём ли мы текст отзыва
        if context.user_data.get('waiting_review_text'):
            await self.handle_review_text(update, context)
            return

        # Иначе показываем меню
        await update.message.reply_text(
            "Используй меню для навигации 👇",
            reply_markup=self.get_main_menu_keyboard()
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        await update.message.reply_text(
            "Нажми /start для открытия главного меню",
            reply_markup=self.get_main_menu_keyboard()
        )

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика (только для админа)"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("Эта команда доступна только администратору.")
            return

        total_reviews = len(user_reviews)
        avg_rating = sum(r['rating'] for r in user_reviews) / len(user_reviews) if user_reviews else 0

        stats_text = f"""
📊 **Статистика бота**

⭐ Всего отзывов: {total_reviews}
📈 Средняя оценка: {avg_rating:.1f}/5
⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 Лицензии теперь хранятся в БД - используй /api/v1/telegram для статистики
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    def run(self):
        """Запуск бота"""
        logger.info("Starting SheetGPT Telegram Bot v2.0...")

        # Инициализируем подключение к БД
        self._init_db()

        # Создаем приложение
        self.application = Application.builder().token(self.token).build()

        # Регистрируем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.admin_stats))

        # Обработчик callback-кнопок
        self.application.add_handler(CallbackQueryHandler(self.menu_callback))

        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Создаём event loop для потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Запускаем бота
        logger.info("Bot is running...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)


def main():
    """Точка входа"""
    from app.config import settings

    token = settings.TELEGRAM_BOT_TOKEN
    admin_id = settings.TELEGRAM_ADMIN_ID
    database_url = settings.DATABASE_URL

    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    if not admin_id:
        logger.warning("TELEGRAM_ADMIN_ID not set - admin commands will be disabled")

    bot = SheetGPTBot(token=token, admin_id=admin_id, database_url=database_url)
    bot.run()


if __name__ == "__main__":
    main()
