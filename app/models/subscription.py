from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class Subscription(Base):
    """Модель подписки"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Детали подписки
    tier = Column(String(20), nullable=False)  # starter, pro, team
    status = Column(String(20), default="active")  # active, cancelled, expired
    price = Column(Integer, nullable=False)  # В копейках (490₽ = 49000)
    billing_cycle = Column(String(20), default="monthly")  # monthly, yearly

    # Даты
    next_billing_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    cancelled_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Subscription {self.tier} - {self.status}>"
