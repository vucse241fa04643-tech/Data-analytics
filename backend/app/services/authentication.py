"""
Agent 63 – Authentication Service
Manages credential verification, JWT token issuance, token verification,
and stateful token revocation. Strictly prevents stale token claims from bypassing
current server-side authorization state.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
import uuid
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
    InvalidTokenError,
    InvalidAlgorithmError,
    InvalidIssuerError,
    InvalidAudienceError,
)

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError
from backend.app.core.logging import get_logger
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.identity_repository import (
    IdentityRepository,
    InMemoryIdentityRepository,
    get_identity_repository,
)
from backend.app.services.password import PasswordManager, get_password_manager
from backend.app.services.token_revocation import (
    TokenRevocationStore,
    get_token_revocation_store,
)

logger = get_logger("agent63.services.authentication")


class AuthenticationService:
    """Core authentication logic for Agent 63 institutional API."""

    def __init__(
        self,
        identity_repo: Optional[IdentityRepository] = None,
        password_mgr: Optional[PasswordManager] = None,
        revocation_store: Optional[TokenRevocationStore] = None,
    ):
        self._identity_repo = identity_repo or get_identity_repository()
        self._password_mgr = password_mgr or get_password_manager()
        self._revocation_store = revocation_store or get_token_revocation_store()

    def authenticate_user(self, username: str, password: str) -> Optional[AuthenticatedPrincipal]:
        """
        Validates institutional credentials and returns the AuthenticatedPrincipal.
        Performs constant-time evaluation; returns None on failure without revealing
        whether the account or password exists.
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        if not username or not password:
            return None

        # Clean sanitized username lookup
        clean_username = username.strip().lower()
        user_record = self._identity_repo.get_user_by_username(clean_username)

        # In-memory repo credential check (or future DB credential table)
        stored_hash: Optional[str] = None
        if user_record and isinstance(self._identity_repo, InMemoryIdentityRepository):
            stored_hash = self._identity_repo.get_credential_hash(user_record["user_id"])

        # Constant-time dummy verification if user not found to prevent timing enumeration
        if not user_record or not stored_hash:
            # Hash a dummy string to equalize response timing
            self._password_mgr.verify_password(
                "dummy_password",
                "$argon2id$v=19$m=65536,t=2,p=1$c29tZXNhbHQxMjM0NTY3OA$9gT23U5J2R3fQ5aX6s7d8e9f0g1h2i3j4k5l6m7n8o",
            )
            logger.info("Authentication failed: invalid credentials or unknown user")
            return None

        # Verify password
        is_valid = self._password_mgr.verify_password(password, stored_hash)
        if not is_valid:
            logger.info("Authentication failed: invalid credentials or unknown user")
            return None

        # Check account active state
        if not user_record.get("is_active", True):
            logger.info(f"Authentication failed: account is inactive for user {clean_username}")
            raise AuthenticationError("Account is inactive or disabled.")

        # Resolve trusted principal server-side
        principal = self._identity_repo.resolve_principal(user_record["user_id"])
        if not principal or not principal.is_active:
            raise AuthenticationError("Account is inactive or disabled.")

        logger.info(f"User authenticated successfully: user_id={principal.user_id}")
        return principal

    def create_access_token(self, principal: AuthenticatedPrincipal) -> Tuple[str, int, str]:
        """
        Signs and issues a cryptographically verified JWT bearer token.
        Claims are strictly minimal: sub, jti, iat, nbf, exp, iss, aud.
        All authorization state (roles, permissions, scopes) is resolved server-side.
        Returns (token_string, expires_in_seconds, jti).
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = now + expires_delta
        expires_in = int(expires_delta.total_seconds())
        jti = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "sub": str(principal.user_id),
            "jti": jti,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        # Algorithm allowlist enforcement
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return token, expires_in, jti

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """
        Verifies token signature, expiration, issuer, audience, and revocation status.
        Raises AuthenticationError if invalid, expired, revoked, or untrusted.
        """
        if not token:
            raise AuthenticationError("Authentication token is missing.")

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],  # Explicit algorithm allowlist
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
                options={"require": ["sub", "exp", "jti", "iss", "aud", "iat", "nbf"]},
            )
        except ExpiredSignatureError:
            raise AuthenticationError("Authentication token has expired.")
        except InvalidSignatureError:
            raise AuthenticationError("Invalid token signature.")
        except InvalidAlgorithmError:
            raise AuthenticationError("Invalid token signing algorithm.")
        except (InvalidIssuerError, InvalidAudienceError):
            raise AuthenticationError("Invalid token issuer or audience.")
        except (DecodeError, InvalidTokenError) as e:
            raise AuthenticationError(f"Malformed or invalid authentication token: {e}")

        # Check token revocation
        jti = payload.get("jti")
        if self._revocation_store.is_revoked(jti):
            logger.info(f"Rejected revoked token: jti={jti[:8]}***")
            raise AuthenticationError("Authentication token has been revoked.")

        return payload

    def get_principal_from_token(self, token: str) -> AuthenticatedPrincipal:
        """
        Validates token and resolves CURRENT trusted roles/permissions from the identity repository.
        CRITICAL: Never trusts client or token-embedded roles; always resolves server-side state.
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        payload = self.verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token subject.")

        principal = self._identity_repo.resolve_principal(user_id)
        if not principal:
            raise AuthenticationError("Authenticated user no longer exists or identity provider is unavailable.")

        if not principal.is_active:
            raise AuthenticationError("Account is inactive or disabled.")

        return principal

    def logout_token(self, token: str) -> bool:
        """
        Revokes the token JTI in the revocation store, preventing further use.
        """
        try:
            payload = self.verify_access_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti:
                self._revocation_store.revoke_token(jti, float(exp) if exp else None)
                return True
            return False
        except AuthenticationError:
            # Already invalid or expired
            return True


# Singleton instance
_authentication_service: Optional[AuthenticationService] = None


def get_authentication_service() -> AuthenticationService:
    global _authentication_service
    if _authentication_service is None:
        _authentication_service = AuthenticationService()
    return _authentication_service


def reset_authentication_service() -> None:
    """Resets global singleton authentication service for isolated test runs."""
    global _authentication_service
    _authentication_service = None

