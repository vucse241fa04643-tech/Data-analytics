"""
Agent 63 – Password Security & Hashing Service
Uses Argon2id via argon2-cffi for enterprise-grade cryptographic password protection.
Guarantees constant-time verification, salted hashes, and zero plaintext retention.
"""

from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from backend.app.core.logging import get_logger

logger = get_logger("agent63.services.password")


class PasswordManager:
    """Manages password hashing and verification using Argon2id."""

    def __init__(
        self,
        time_cost: int = 2,
        memory_cost: int = 65536,  # 64 MB
        parallelism: int = 1,
        hash_len: int = 32,
        salt_len: int = 16,
    ):
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash_password(self, password: str) -> str:
        """Computes a cryptographically secure Argon2id hash with a random unique salt."""
        if not password:
            raise ValueError("Password cannot be empty.")
        return self._hasher.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifies plaintext password against stored hash in constant-time.
        Returns False on mismatch or corrupted hash without raising exceptions.
        """
        if not password or not hashed_password:
            return False
        try:
            return self._hasher.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        except Exception as e:
            logger.error(f"Unexpected error during password verification: {e}")
            return False

    def check_needs_rehash(self, hashed_password: str) -> bool:
        """Determines if the hash was created with older, weaker cost parameters."""
        try:
            return self._hasher.check_needs_rehash(hashed_password)
        except Exception:
            return False


# Singleton password manager
_password_manager: Optional[PasswordManager] = None


def get_password_manager() -> PasswordManager:
    global _password_manager
    if _password_manager is None:
        _password_manager = PasswordManager()
    return _password_manager
