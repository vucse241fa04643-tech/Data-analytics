"""Agent 63 - Phase 10: Conversation Context Store
Defines the storage abstraction and in-memory, thread-safe, bounded implementation for conversation contexts.
Enforces per-user ownership verification, strict TTL expiration, LRU eviction, and memory bounds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timezone
import threading
from typing import Optional, Union

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.schemas.conversation_context import ConversationContext
from backend.app.schemas.principal import AuthenticatedPrincipal

logger = get_logger("agent63.services.conversation_store")


class ConversationContextStore(ABC):
    """Abstract contract for conversation context persistence."""

    @abstractmethod
    def get_context(
        self, conversation_id: str, principal: AuthenticatedPrincipal
    ) -> Optional[ConversationContext]:
        """
        Retrieves context for conversation_id only if owned by the authenticated principal
        and not expired. Returns None if not found, owned by another user, or expired.
        """
        pass

    @abstractmethod
    def save_context(self, context: ConversationContext) -> None:
        """Stores or updates conversation context enforcing capacity and byte size bounds."""
        pass

    @abstractmethod
    def clear_context(
        self, conversation_id: str, principal: AuthenticatedPrincipal
    ) -> bool:
        """Removes a conversation context if owned by the authenticated principal."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns the number of active stored conversations."""
        pass


class InMemoryConversationContextStore(ConversationContextStore):
    """
    Thread-safe, in-memory conversation context store with LRU eviction and strict TTL checks.
    Isolates contexts by authenticated user ID.
    """

    def __init__(
        self,
        max_entries: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
        default_ttl_seconds: Optional[int] = None,
    ):
        self._max_entries = max_entries or settings.CONVERSATION_MAX_ENTRIES
        self._max_size_bytes = max_size_bytes or settings.CONVERSATION_MAX_SIZE_BYTES
        self._default_ttl_seconds = default_ttl_seconds or settings.CONVERSATION_CONTEXT_TTL_SECONDS
        self._store: OrderedDict[str, ConversationContext] = OrderedDict()
        self._lock = threading.RLock()

    def get_context(
        self, conversation_id: str, principal: Union[AuthenticatedPrincipal, str]
    ) -> Optional[ConversationContext]:
        """Retrieves context with ownership and TTL enforcement."""
        user_id = principal.user_id if isinstance(principal, AuthenticatedPrincipal) else str(principal)
        with self._lock:
            if conversation_id not in self._store:
                return None

            ctx = self._store[conversation_id]

            # Security Rule: Enforce user isolation
            if ctx.user_id != user_id:
                logger.warning(
                    f"Cross-user conversation context access attempt blocked: "
                    f"actor='{user_id}' target_conv='{conversation_id}' owner='{ctx.user_id}'"
                )
                return None

            # Enforce TTL expiration
            if ctx.is_expired():
                logger.info(f"Conversation context expired: conv_id='{conversation_id}'")
                del self._store[conversation_id]
                return None

            # Mark as recently accessed for LRU
            self._store.move_to_end(conversation_id)
            return ctx

    def save_context(self, context: ConversationContext) -> None:
        """Stores conversation context with size limits and LRU capacity enforcement."""
        with self._lock:
            # Enforce payload size ceiling (defense against memory exhaustion)
            serialized = context.model_dump_json()
            if len(serialized.encode("utf-8")) > self._max_size_bytes:
                logger.warning(
                    f"Conversation context exceeds maximum byte ceiling: "
                    f"conv_id='{context.conversation_id}' size={len(serialized.encode('utf-8'))}"
                )
                raise ValueError("Conversation context payload size exceeds maximum allowed limit.")

            # Evict oldest if at capacity
            if context.conversation_id not in self._store and len(self._store) >= self._max_entries:
                evicted_id, _ = self._store.popitem(last=False)
                logger.info(f"Evicted oldest conversation context via LRU: conv_id='{evicted_id}'")

            self._store[context.conversation_id] = context
            self._store.move_to_end(context.conversation_id)

    def clear_context(
        self, conversation_id: str, principal: Union[AuthenticatedPrincipal, str]
    ) -> bool:
        """Clears a conversation context if owned by principal."""
        user_id = principal.user_id if isinstance(principal, AuthenticatedPrincipal) else str(principal)
        with self._lock:
            if conversation_id not in self._store:
                return False

            ctx = self._store[conversation_id]
            if ctx.user_id != user_id:
                logger.warning(
                    f"Unauthorized attempt to clear conversation: actor='{user_id}' owner='{ctx.user_id}'"
                )
                return False

            del self._store[conversation_id]
            logger.info(f"Cleared conversation context: conv_id='{conversation_id}'")
            return True

    def count(self) -> int:
        """Returns the current number of active conversations in memory."""
        with self._lock:
            # Prune expired on count check
            now = datetime.now(timezone.utc)
            expired_keys = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired_keys:
                del self._store[k]
            return len(self._store)


_conversation_store: Optional[ConversationContextStore] = None


def get_conversation_store() -> ConversationContextStore:
    """Returns singleton instance of ConversationContextStore."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = InMemoryConversationContextStore()
    return _conversation_store
