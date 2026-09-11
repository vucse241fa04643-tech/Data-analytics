"""
Agent 63 – Token Revocation Store
Implements a stateful token revocation abstraction using JWT JTI (JWT ID).
Ensures that logged-out or invalidated tokens cannot be reused.

IMPORTANT ARCHITECTURAL LIMITATION NOTICE:
- The current Phase 5 implementation (InMemoryTokenRevocationStore) revokes tokens
  for the lifetime of the running process only.
- Revocation state is maintained in-memory and is lost after process restart.
- The TokenRevocationStore abstraction is intentionally designed so that a future
  persistent PostgreSQL table or Redis cache can be plugged in without changing
  API contracts or service signatures.
- PostgreSQL and Redis are NOT implemented in Phase 5.
"""

from abc import ABC, abstractmethod
import time
from typing import Dict, Optional, Set
import threading

from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.token_revocation")


class TokenRevocationStore(ABC):
    """Abstract interface for checking and registering revoked JWT tokens."""

    @abstractmethod
    def revoke_token(self, jti: str, expires_at: Optional[float] = None) -> None:
        """Marks a token identifier (JTI) as permanently revoked."""
        pass

    @abstractmethod
    def is_revoked(self, jti: str) -> bool:
        """Evaluates whether the specified token identifier has been revoked."""
        pass


class InMemoryTokenRevocationStore(TokenRevocationStore):
    """
    Thread-safe in-memory token revocation repository.
    Used for local execution and unit tests; tracks revoked JTIs with expiration pruning.

    Limitation: Revocation state is ephemeral and retained only for the process lifetime.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Maps jti -> expires_at timestamp
        self._revoked_tokens: Dict[str, float] = {}

    def revoke_token(self, jti: str, expires_at: Optional[float] = None) -> None:
        if not jti:
            return
        now = time.time()
        # Default expiration buffer if not provided: 24 hours
        exp = expires_at if expires_at is not None else now + 86400.0

        with self._lock:
            # Periodic cleanup of expired tokens
            self._cleanup_expired_locked(now)
            self._revoked_tokens[jti] = exp

        logger.info(f"Token revoked successfully: jti={jti[:8]}***")

    def is_revoked(self, jti: str) -> bool:
        if not jti:
            return True
        now = time.time()
        with self._lock:
            if jti in self._revoked_tokens:
                if self._revoked_tokens[jti] > now:
                    return True
                # Clean up expired entry
                del self._revoked_tokens[jti]
                return False
        return False

    def _cleanup_expired_locked(self, current_time: float) -> None:
        expired = [jti for jti, exp in self._revoked_tokens.items() if exp <= current_time]
        for jti in expired:
            del self._revoked_tokens[jti]


# Singleton instance
_token_revocation_store: Optional[TokenRevocationStore] = None


def get_token_revocation_store() -> TokenRevocationStore:
    global _token_revocation_store
    if _token_revocation_store is None:
        _token_revocation_store = InMemoryTokenRevocationStore()
    return _token_revocation_store


def reset_token_revocation_store() -> None:
    """Resets global singleton revocation store for isolated test runs."""
    global _token_revocation_store
    _token_revocation_store = None

