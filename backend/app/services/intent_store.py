"""
In-memory store для Intent objects и Conversation History

Используется для хранения Intent между запросами во время clarification flow
И для отслеживания истории разговора для контекстных запросов
"""

from typing import Dict, Optional, List, Any
from uuid import uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from app.services.intent_parser import Intent


@dataclass
class ConversationTurn:
    """Один turn в разговоре (запрос + ответ)"""
    query: str
    intent: Optional[Intent]
    result: Optional[Dict[str, Any]]  # action или clarification questions
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    """История разговора"""
    conversation_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_turn(self, query: str, intent: Optional[Intent], result: Optional[Dict[str, Any]]):
        """Добавляет новый turn в разговор"""
        turn = ConversationTurn(query=query, intent=intent, result=result)
        self.turns.append(turn)
        self.last_updated = datetime.now()

    def get_last_successful_intent(self) -> Optional[Intent]:
        """Возвращает последний успешный intent (где result.success=True)"""
        for turn in reversed(self.turns):
            if turn.intent and turn.result and turn.result.get("success"):
                return turn.intent
        return None

    def get_last_query(self) -> Optional[str]:
        """Возвращает последний запрос"""
        if self.turns:
            return self.turns[-1].query
        return None


class IntentStore:
    """
    Простое in-memory хранилище для Intent и Conversation History

    TODO: В production заменить на Redis для масштабируемости
    """

    def __init__(self, ttl_minutes: int = 30):
        """
        Args:
            ttl_minutes: Время жизни Intent и Conversation в минутах
        """
        self._store: Dict[str, tuple[Intent, datetime]] = {}
        self._conversations: Dict[str, Conversation] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def save(self, intent: Intent) -> str:
        """
        Сохраняет Intent и возвращает уникальный ID

        Returns:
            intent_id для последующего извлечения
        """
        intent_id = str(uuid4())
        self._store[intent_id] = (intent, datetime.now())
        return intent_id

    def get(self, intent_id: str) -> Optional[Intent]:
        """
        Извлекает Intent по ID

        Returns:
            Intent или None если не найден или истек
        """
        if intent_id not in self._store:
            return None

        intent, saved_at = self._store[intent_id]

        # Проверяем TTL
        if datetime.now() - saved_at > self.ttl:
            del self._store[intent_id]
            return None

        return intent

    def delete(self, intent_id: str) -> bool:
        """Удаляет Intent из store"""
        if intent_id in self._store:
            del self._store[intent_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Удаляет все истекшие Intent

        Returns:
            Количество удаленных Intent
        """
        now = datetime.now()
        expired = [
            intent_id
            for intent_id, (_, saved_at) in self._store.items()
            if now - saved_at > self.ttl
        ]

        for intent_id in expired:
            del self._store[intent_id]

        return len(expired)

    # ===== Conversation History методы =====

    def create_conversation(self) -> str:
        """
        Создает новый разговор

        Returns:
            conversation_id для последующего использования
        """
        conversation_id = str(uuid4())
        conversation = Conversation(conversation_id=conversation_id)
        self._conversations[conversation_id] = conversation
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Получает Conversation по ID

        Returns:
            Conversation или None если не найден или истек
        """
        if conversation_id not in self._conversations:
            return None

        conversation = self._conversations[conversation_id]

        # Проверяем TTL
        if datetime.now() - conversation.last_updated > self.ttl:
            del self._conversations[conversation_id]
            return None

        return conversation

    def add_conversation_turn(
        self,
        conversation_id: str,
        query: str,
        intent: Optional[Intent],
        result: Optional[Dict[str, Any]]
    ):
        """
        Добавляет turn в существующий разговор

        Если conversation_id не существует, создает новый
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            # Создаем новый разговор с этим ID
            conversation = Conversation(conversation_id=conversation_id)
            self._conversations[conversation_id] = conversation

        conversation.add_turn(query, intent, result)

    def cleanup_expired_conversations(self) -> int:
        """
        Удаляет все истекшие разговоры

        Returns:
            Количество удаленных разговоров
        """
        now = datetime.now()
        expired = [
            conv_id
            for conv_id, conv in self._conversations.items()
            if now - conv.last_updated > self.ttl
        ]

        for conv_id in expired:
            del self._conversations[conv_id]

        return len(expired)


# Глобальный экземпляр
intent_store = IntentStore(ttl_minutes=30)
