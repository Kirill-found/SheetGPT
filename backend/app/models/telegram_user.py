"""
Модель для Telegram пользователей SheetGPT Bot
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import secrets
from app.core.database import Base


class TelegramUser(Base):
    """Модель пользователя Telegram бота"""
    __tablename__ = "telegram_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Telegram данные
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))

    # API токен для аутентификации
    api_token = Column(String(64), unique=True, nullable=False, index=True)

    # Лицензионный ключ для Chrome Extension (формат: XXXX-XXXX-XXXX-XXXX)
    license_key = Column(String(19), unique=True, nullable=True, index=True)

    # Подписка и лимиты
    subscription_tier = Column(String(20), default="free")  # free, premium
    is_active = Column(Boolean, default=True)

    # Лимиты запросов
    queries_used_today = Column(Integer, default=0)
    queries_limit = Column(Integer, default=10)  # free: 10, premium: unlimited (-1)

    # Статистика
    total_queries = Column(Integer, default=0)
    last_query_at = Column(DateTime(timezone=True))

    # Реферальная система
    referral_code = Column(String(50), nullable=True, index=True)  # Код партнёра (ref_БЛОГЕР)
    referred_at = Column(DateTime(timezone=True))  # Когда пришёл по реферальной ссылке

    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    premium_until = Column(DateTime(timezone=True))  # Дата истечения premium подписки

    @staticmethod
    def generate_api_token():
        """Генерация уникального API токена"""
        return secrets.token_urlsafe(48)

    @staticmethod
    def generate_license_key():
        """Генерация лицензионного ключа формата XXXX-XXXX-XXXX-XXXX"""
        parts = [secrets.token_hex(2).upper() for _ in range(4)]
        return '-'.join(parts)

    def can_make_query(self) -> bool:
        """Проверка возможности сделать запрос"""
        if not self.is_active:
            return False

        # queries_limit = -1 означает безлимит (независимо от tier)
        if self.queries_limit == -1:
            return True

        # Premium пользователи имеют безлимит
        if self.subscription_tier == "premium":
            # Проверяем, не истекла ли подписка
            if self.premium_until:
                from datetime import datetime, timezone
                if datetime.now(timezone.utc) > self.premium_until:
                    # Подписка истекла - понижаем до free
                    return self.queries_used_today < 10  # default free limit
            return True

        # Free пользователи ограничены дневным лимитом
        return self.queries_used_today < self.queries_limit

    def upgrade_to_premium(self, duration_days: int = 30):
        """Обновление до Premium подписки"""
        from datetime import datetime, timezone, timedelta
        self.subscription_tier = "premium"
        self.queries_limit = -1  # Unlimited
        self.queries_used_today = 0  # Reset usage
        self.premium_until = datetime.now(timezone.utc) + timedelta(days=duration_days)

    def downgrade_to_free(self):
        """Понижение до Free плана"""
        self.subscription_tier = "free"
        self.queries_limit = 10
        self.queries_used_today = 0
        self.premium_until = None

    def increment_usage(self):
        """Увеличение счетчика использования"""
        self.queries_used_today += 1
        self.total_queries += 1
        from datetime import datetime, timezone
        self.last_query_at = datetime.now(timezone.utc)

    def reset_daily_usage(self):
        """Сброс дневного счетчика (вызывается ежедневно)"""
        self.queries_used_today = 0

    def __repr__(self):
        return f"<TelegramUser {self.telegram_user_id} - {self.subscription_tier}>"
