"""
Админ-команды для Telegram бота SheetGPT
"""
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, func
from app.models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)


class AdminCommands:
    """Класс с админ-командами для Telegram бота"""

    def __init__(self, admin_id: int, session_factory):
        self.admin_id = admin_id
        self.session_factory = session_factory

    def _check_admin(self, user_id: int) -> bool:
        """Проверка что пользователь - админ"""
        return user_id == self.admin_id

    async def _reply(self, update: Update, text: str, parse_mode: str = 'Markdown', reply_markup=None):
        """Универсальный метод для ответа - работает и с message, и с callback_query"""
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(
                    text, parse_mode=parse_mode, reply_markup=reply_markup
                )
            except Exception:
                await update.effective_chat.send_message(
                    text, parse_mode=parse_mode, reply_markup=reply_markup
                )
        elif update.message:
            await update.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup
            )

    async def _send_document(self, update: Update, document, filename: str, caption: str = None):
        """Универсальный метод для отправки документа"""
        if update.callback_query:
            await update.callback_query.answer()
            await update.effective_chat.send_document(
                document=document, filename=filename, caption=caption
            )
        elif update.message:
            await update.message.reply_document(
                document=document, filename=filename, caption=caption
            )

    async def admin_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Команда /dashboard - полная админ-панель с детальной статистикой

        Показывает:
        - Общее количество пользователей
        - Количество платящих/бесплатных пользователей
        - Конверсию в платящих
        - Активность за разные периоды
        - Топ активных пользователей
        """
        if not self._check_admin(update.effective_user.id):
            await self._reply(update, "⛔ Эта команда доступна только администратору.")
            return

        if not self.session_factory:
            await self._reply(update, "❌ База данных не подключена")
            return

        async with self.session_factory() as session:
            # Общее количество пользователей
            total_users = await session.execute(select(func.count(TelegramUser.id)))
            total_count = total_users.scalar() or 0

            # Платящие пользователи
            premium_users = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.subscription_tier == 'premium')
            )
            premium_count = premium_users.scalar() or 0

            # Бесплатные пользователи
            free_count = total_count - premium_count

            # Конверсия
            conversion = (premium_count / total_count * 100) if total_count > 0 else 0

            # MRR (Monthly Recurring Revenue)
            # Считаем активных premium (у которых premium_until > сейчас)
            now = datetime.now(timezone.utc)
            active_premium = await session.execute(
                select(TelegramUser).where(
                    TelegramUser.subscription_tier == 'premium',
                    TelegramUser.premium_until > now
                )
            )
            active_premium_users = active_premium.scalars().all()
            
            # Расчет MRR: считаем каждого по месячной ставке 299 руб
            mrr = len(active_premium_users) * 299
            
            # ARR (Annual Recurring Revenue)
            arr = mrr * 12

            # Активные пользователи (запросы за последние 7 дней)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            active_7d = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.last_query_at >= week_ago)
            )
            active_7d_count = active_7d.scalar() or 0

            # Активные за последние 24 часа
            day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            active_24h = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.last_query_at >= day_ago)
            )
            active_24h_count = active_24h.scalar() or 0

            # Новые пользователи за 24 часа
            new_24h = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.created_at >= day_ago)
            )
            new_24h_count = new_24h.scalar() or 0

            # Новые пользователи за 7 дней
            new_7d = await session.execute(
                select(func.count(TelegramUser.id)).where(TelegramUser.created_at >= week_ago)
            )
            new_7d_count = new_7d.scalar() or 0

            # Общее количество запросов
            total_queries = await session.execute(select(func.sum(TelegramUser.total_queries)))
            total_queries_count = total_queries.scalar() or 0

            # Запросы за сегодня
            queries_today = await session.execute(select(func.sum(TelegramUser.queries_used_today)))
            queries_today_count = queries_today.scalar() or 0

            # Среднее количество запросов на пользователя
            avg_queries = (total_queries_count / total_count) if total_count > 0 else 0

            # Топ-5 активных пользователей
            top_users = await session.execute(
                select(TelegramUser).order_by(TelegramUser.total_queries.desc()).limit(5)
            )
            top_users_list = top_users.scalars().all()

            # Недавно зарегистрированные (последние 5)
            recent_users = await session.execute(
                select(TelegramUser).order_by(TelegramUser.created_at.desc()).limit(5)
            )
            recent_users_list = recent_users.scalars().all()

        active_pro_count = len(active_premium_users)
        
        # Формируем сообщение
        text = f"""
📊 **АДМИН-ПАНЕЛЬ SheetGPT**

━━━━━━━━━━━━━━━━━━━━

👥 **ПОЛЬЗОВАТЕЛИ**
• Всего: **{total_count}**
• 💎 Premium: **{premium_count}** ({conversion:.1f}%)
• 🆓 Free: **{free_count}**

💰 **ДОХОД**
• MRR: **{mrr:,}** ₽
• ARR: **{arr:,}** ₽
• Активных PRO: **{active_pro_count}**

📈 **РОСТ**
• Новых за 24ч: **{new_24h_count}**
• Новых за 7д: **{new_7d_count}**

⚡ **АКТИВНОСТЬ**
• Активных за 24ч: **{active_24h_count}**
• Активных за 7д: **{active_7d_count}**

📊 **ЗАПРОСЫ**
• Всего: **{total_queries_count:,}**
• Сегодня: **{queries_today_count}**
• Среднее/юзер: **{avg_queries:.1f}**

━━━━━━━━━━━━━━━━━━━━

🏆 **ТОП-5 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ**
"""

        for i, user in enumerate(top_users_list, 1):
            tier = "💎" if user.subscription_tier == "premium" else "🆓"
            name = user.first_name or user.username or f"ID{user.telegram_user_id}"
            text += f"{i}. {tier} {name}\n"
            text += f"   └ {user.total_queries:,} запросов всего\n"

        text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "🆕 **ПОСЛЕДНИЕ РЕГИСТРАЦИИ**\n"

        for user in recent_users_list:
            tier = "💎" if user.subscription_tier == "premium" else "🆓"
            name = user.first_name or user.username or f"ID{user.telegram_user_id}"
            reg_date = user.created_at.strftime('%d.%m %H:%M')
            text += f"• {tier} {name}\n"
            text += f"  └ {reg_date} | {user.total_queries} запросов\n"

        text += f"\n⏰ Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"

        # Кнопки управления
        keyboard = [
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh"),
                InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("💎 Premium", callback_data="admin_premium"),
                InlineKeyboardButton("🆓 Free", callback_data="admin_free")
            ],
            [
                InlineKeyboardButton("📊 Экспорт данных", callback_data="admin_export")
            ]
        ]

        await self._reply(update, 
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def admin_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /users - список пользователей с пагинацией"""
        if not self._check_admin(update.effective_user.id):
            await self._reply(update, "⛔ Только для администратора")
            return

        page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
        per_page = 20
        offset = (page - 1) * per_page

        async with self.session_factory() as session:
            # Получаем пользователей с пагинацией
            users_query = await session.execute(
                select(TelegramUser)
                .order_by(TelegramUser.created_at.desc())
                .limit(per_page)
                .offset(offset)
            )
            users = users_query.scalars().all()

            # Общее количество
            total = await session.execute(select(func.count(TelegramUser.id)))
            total_count = total.scalar()

        if not users:
            await self._reply(update, "Пользователей не найдено")
            return

        total_pages = (total_count + per_page - 1) // per_page

        text = f"👥 **Пользователи** (стр. {page}/{total_pages})\n\n"

        for user in users:
            tier = "💎" if user.subscription_tier == "premium" else "🆓"
            name = user.first_name or user.username or f"ID{user.telegram_user_id}"
            text += f"{tier} {name}\n"
            text += f"  License: `{user.license_key}`\n"
            text += f"  Запросов: {user.total_queries} (сегодня: {user.queries_used_today}/{user.queries_limit})\n"
            if user.last_query_at:
                last = user.last_query_at.strftime('%d.%m %H:%M')
                text += f"  Последний: {last}\n"
            text += "\n"

        # Кнопки пагинации
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
        if page < total_pages:
            buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"admin_users_page_{page+1}"))

        keyboard = [buttons] if buttons else []

        await self._reply(update, 
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )

    async def admin_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /user <license_key> - детальная информация о пользователе"""
        if not self._check_admin(update.effective_user.id):
            await self._reply(update, "⛔ Только для администратора")
            return

        if not context.args:
            await self._reply(update, "Использование: /user <license_key>")
            return

        license_key = context.args[0]

        async with self.session_factory() as session:
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

        if not user:
            await self._reply(update, f"❌ Пользователь с ключом `{license_key}` не найден")
            return

        tier = "💎 Premium" if user.subscription_tier == "premium" else "🆓 Free"
        status = "✅ Активен" if user.is_active else "❌ Заблокирован"

        text = f"""
👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**

**Основное:**
• Имя: {user.first_name or 'N/A'}
• Username: @{user.username or 'N/A'}
• Telegram ID: `{user.telegram_user_id}`
• License Key: `{user.license_key}`

**Подписка:**
• Тариф: {tier}
• Статус: {status}
• Лимит: {user.queries_limit} запросов/день
"""

        if user.premium_until:
            premium_date = user.premium_until.strftime('%d.%m.%Y %H:%M')
            text += f"• Premium до: {premium_date}\n"

        text += f"""
**Активность:**
• Всего запросов: {user.total_queries}
• Использовано сегодня: {user.queries_used_today}/{user.queries_limit}
"""

        if user.last_query_at:
            last_query = user.last_query_at.strftime('%d.%m.%Y %H:%M')
            text += f"• Последний запрос: {last_query}\n"

        reg_date = user.created_at.strftime('%d.%m.%Y %H:%M')
        text += f"\n• Регистрация: {reg_date}"

        # Кнопки управления
        keyboard = [
            [
                InlineKeyboardButton("⭐ Дать Premium", callback_data=f"admin_grant_{user.telegram_user_id}"),
                InlineKeyboardButton("❌ Забрать Premium", callback_data=f"admin_revoke_{user.telegram_user_id}")
            ],
            [
                InlineKeyboardButton("🚫 Заблокировать", callback_data=f"admin_block_{user.telegram_user_id}") if user.is_active else
                InlineKeyboardButton("✅ Разблокировать", callback_data=f"admin_unblock_{user.telegram_user_id}")
            ]
        ]

        await self._reply(update, 
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def admin_grant_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /grant <license_key> [days] - выдать Premium подписку"""
        if not self._check_admin(update.effective_user.id):
            await self._reply(update, "⛔ Только для администратора")
            return

        if not context.args:
            await self._reply(update, "Использование: /grant <license_key> [days=365]")
            return

        license_key = context.args[0]
        days = int(context.args[1]) if len(context.args) > 1 else 365

        async with self.session_factory() as session:
            result = await session.execute(
                select(TelegramUser).where(TelegramUser.license_key == license_key)
            )
            user = result.scalar_one_or_none()

            if not user:
                await self._reply(update, f"❌ Пользователь с ключом `{license_key}` не найден")
                return

            user.upgrade_to_premium(duration_days=days)
            await session.commit()

        premium_until = user.premium_until.strftime('%d.%m.%Y')
        await self._reply(update, 
            f"✅ Premium выдан!\n\n"
            f"👤 {user.first_name or user.username}\n"
            f"🔑 `{license_key}`\n"
            f"⏰ До: {premium_until}"
        )

    async def admin_export_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /export - экспорт данных пользователей в CSV"""
        if not self._check_admin(update.effective_user.id):
            await self._reply(update, "⛔ Только для администратора")
            return

        import csv
        import io

        async with self.session_factory() as session:
            result = await session.execute(
                select(TelegramUser).order_by(TelegramUser.created_at.desc())
            )
            users = result.scalars().all()

        # Создаем CSV в памяти
        output = io.StringIO()
        writer = csv.writer(output)

        # Заголовки
        writer.writerow([
            'License Key', 'Telegram ID', 'Username', 'First Name',
            'Tier', 'Queries Total', 'Queries Today', 'Queries Limit',
            'Created At', 'Last Query At', 'Premium Until'
        ])

        # Данные
        for user in users:
            writer.writerow([
                user.license_key,
                user.telegram_user_id,
                user.username or '',
                user.first_name or '',
                user.subscription_tier,
                user.total_queries,
                user.queries_used_today,
                user.queries_limit,
                user.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                user.last_query_at.strftime('%Y-%m-%d %H:%M:%S') if user.last_query_at else '',
                user.premium_until.strftime('%Y-%m-%d %H:%M:%S') if user.premium_until else ''
            ])

        # Отправляем файл
        output.seek(0)
        filename = f"sheetgpt_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        await self._send_document(update, document=io.BytesIO(output.getvalue().encode('utf-8')), filename=filename, caption=f"📊 Экспорт данных\n\nВсего пользователей: {len(users)}"
        )
