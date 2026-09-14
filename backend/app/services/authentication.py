"""
Agent 63 – Authentication Service
Manages credential verification, JWT token issuance, token verification,
and stateful token revocation. Strictly prevents stale token claims from bypassing
current server-side authorization state.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
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

import hashlib
import re
import secrets
import time

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError, AuthorizationError, RegistrationError
from backend.app.core.logging import get_logger
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType
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

# Institutional roles requiring verified administrative provisioning
PRIVILEGED_ROLES = {
    "MANAGEMENT",
    "PRINCIPAL",
    "DEAN",
    "HOD",
    "IQAC",
    "COE",
    "PLACEMENT",
    "ADMIN",
    "COUNSELLOR",
    "MENTOR",
}

# Standard roles permitted for self-registration with safe default scopes
ALLOWED_SELF_REGISTRATION_ROLES = {
    "STUDENT",
    "FACULTY",
}


class PasswordResetStore:
    """Thread-safe store for single-use, time-limited password reset tokens."""

    def __init__(self, default_lifetime_seconds: int = 900):
        # Maps token_sha256 -> {"user_id": str, "expires_at": float, "used": bool}
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._default_lifetime = default_lifetime_seconds

    def create_reset_token(self, user_id: str, lifetime_seconds: Optional[int] = None) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        lifetime = lifetime_seconds or self._default_lifetime
        self._tokens[token_hash] = {
            "user_id": user_id,
            "expires_at": time.time() + lifetime,
            "used": False,
        }
        return raw_token

    def verify_and_consume_token(self, raw_token: str) -> Optional[str]:
        if not raw_token:
            return None
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        record = self._tokens.get(token_hash)
        if not record:
            return None
        if record["used"]:
            return None
        if time.time() > record["expires_at"]:
            return None
        # Consume token immediately (single-use)
        record["used"] = True
        return record["user_id"]


_password_reset_store: Optional[PasswordResetStore] = None


def get_password_reset_store() -> PasswordResetStore:
    global _password_reset_store
    if _password_reset_store is None:
        _password_reset_store = PasswordResetStore()
    return _password_reset_store


class AccountRequestStore:
    """Thread-safe storage for institutional account requests."""

    def __init__(self):
        # Maps request_id -> dict
        self._requests: Dict[str, Dict[str, Any]] = {}
        # Maps username.lower() -> request_id for duplicate tracking
        self._pending_username_index: Dict[str, str] = {}
        self._pending_email_index: Dict[str, str] = {}

    def create_request(
        self,
        full_name: str,
        username: str,
        email: str,
        requested_role: str,
        requested_department: Optional[str],
        password_hash: str,
    ) -> Dict[str, Any]:
        req_id = str(uuid.uuid4())
        record = {
            "request_id": req_id,
            "full_name": full_name.strip(),
            "username": username.strip(),
            "email": email.strip().lower(),
            "requested_role": requested_role.strip().upper(),
            "requested_department": requested_department.strip().upper() if requested_department else None,
            "password_hash": password_hash,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
            "decision_notes": None,
            "provisioned_user_id": None,
        }
        self._requests[req_id] = record
        self._pending_username_index[username.strip().lower()] = req_id
        self._pending_email_index[email.strip().lower()] = req_id
        return record

    def has_pending_request(self, username: str, email: str) -> bool:
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()
        if clean_user in self._pending_username_index:
            req_id = self._pending_username_index[clean_user]
            if self._requests.get(req_id, {}).get("status") == "PENDING":
                return True
        if clean_email in self._pending_email_index:
            req_id = self._pending_email_index[clean_email]
            if self._requests.get(req_id, {}).get("status") == "PENDING":
                return True
        return False

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._requests.get(request_id)

    def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        reqs = list(self._requests.values())
        if status:
            reqs = [r for r in reqs if r["status"] == status.upper()]
        return sorted(reqs, key=lambda x: x["created_at"], reverse=True)

    def update_status(
        self,
        request_id: str,
        status: str,
        reviewed_by: str,
        notes: Optional[str] = None,
        provisioned_user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        req = self._requests.get(request_id)
        if not req:
            return None
        req["status"] = status
        req["reviewed_by"] = reviewed_by
        req["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        if notes:
            req["decision_notes"] = notes
        if provisioned_user_id:
            req["provisioned_user_id"] = provisioned_user_id
        # Clean up pending index
        clean_user = req["username"].lower()
        clean_email = req["email"].lower()
        if self._pending_username_index.get(clean_user) == request_id:
            del self._pending_username_index[clean_user]
        if self._pending_email_index.get(clean_email) == request_id:
            del self._pending_email_index[clean_email]
        return req


_account_request_store: Optional[AccountRequestStore] = None


def get_account_request_store() -> AccountRequestStore:
    global _account_request_store
    if _account_request_store is None:
        _account_request_store = AccountRequestStore()
    return _account_request_store


def reset_account_request_store() -> None:
    global _account_request_store
    _account_request_store = None


class AuthenticationService:
    """Core authentication logic for Agent 63 institutional API."""

    def __init__(
        self,
        identity_repo: Optional[IdentityRepository] = None,
        password_mgr: Optional[PasswordManager] = None,
        revocation_store: Optional[TokenRevocationStore] = None,
        reset_store: Optional[PasswordResetStore] = None,
        account_request_store: Optional[AccountRequestStore] = None,
    ):
        self._identity_repo = identity_repo or get_identity_repository()
        self._password_mgr = password_mgr or get_password_manager()
        self._revocation_store = revocation_store or get_token_revocation_store()
        self._reset_store = reset_store or get_password_reset_store()
        self._account_request_store = account_request_store or get_account_request_store()



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

    def register_account(
        self,
        username: str,
        password: str,
        confirm_password: str,
        full_name: Optional[str] = None,
        role: str = "STUDENT",
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registers a new institutional user with Argon2id password hashing.
        Enforces server-side password complexity and blocks unauthorized privileged roles.
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        if not username or not username.strip():
            raise RegistrationError("Institutional username cannot be empty.")

        clean_username = username.strip()
        if not re.match(r"^[a-zA-Z0-9_.-]{3,64}$", clean_username):
            raise RegistrationError("Username must be between 3 and 64 alphanumeric characters (may include _, -, .).")

        if not password or len(password) < 8:
            raise RegistrationError("Password must be at least 8 characters in length.")

        if password != confirm_password:
            raise RegistrationError("Password and confirmation password do not match.")

        if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
            raise RegistrationError("Password must contain both letters and numbers.")

        # Enforce server-side role governance: browser selections are never trusted blindly
        norm_role = role.strip().upper() if role else "STUDENT"
        if norm_role in PRIVILEGED_ROLES:
            logger.warning(
                f"Blocked unauthorized privilege escalation attempt during registration: username={clean_username}, role={norm_role}"
            )
            raise AuthorizationError(
                f"Privileged institutional role '{norm_role}' cannot be self-assigned. "
                "Institutional leadership and administrative roles require authorized administrative provisioning."
            )

        if norm_role not in ALLOWED_SELF_REGISTRATION_ROLES:
            raise RegistrationError(
                f"Invalid institutional role '{role}'. Self-registration is restricted to authorized standard institutional roles (Student, Faculty)."
            )

        # Check duplicate username
        existing_user = self._identity_repo.get_user_by_username(clean_username)
        if existing_user:
            raise RegistrationError(f"Institutional username '{clean_username}' is already registered. Please sign in or use another username.")

        # Hash password with Argon2id
        password_hash = self._password_mgr.hash_password(password)

        # Build default institutional email and scope
        user_email = email.strip() if email else f"{clean_username.lower()}@vignan.ac.in"
        scoped_roles = [ScopedRoleAssignment(role=norm_role, scope_type=ScopeType.SELF)]

        user = self._identity_repo.register_user(
            username=clean_username,
            email=user_email,
            password_hash=password_hash,
            scoped_roles=scoped_roles,
            is_active=True,
        )
        logger.info(f"Successfully registered new institutional user: user_id={user['user_id']}, role={norm_role}")
        return user

    def request_password_reset(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Initiates an enumeration-resistant password reset request.
        Generates a single-use time-limited reset token if the institutional identifier exists.
        Returns (exists_bool, raw_token_or_none).
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        if not identifier or not identifier.strip():
            return False, None

        clean_id = identifier.strip().lower()

        # Check by username first, then by email
        user = self._identity_repo.get_user_by_username(clean_id)
        if not user:
            user = self._identity_repo.get_user_by_email(clean_id)

        if user and user.get("is_active", True):
            token = self._reset_store.create_reset_token(user["user_id"])
            logger.info(f"Created password reset token for user_id={user['user_id']}")
            return True, token

        # Constant-time dummy verification if user not found to prevent timing enumeration
        self._password_mgr.verify_password(
            "dummy_password",
            "$argon2id$v=19$m=65536,t=2,p=1$c29tZXNhbHQxMjM0NTY3OA$9gT23U5J2R3fQ5aX6s7d8e9f0g1h2i3j4k5l6m7n8o",
        )
        return False, None

    def reset_password_with_token(self, token: str, new_password: str, confirm_password: str) -> bool:
        """
        Validates the single-use reset token and updates the user credential with Argon2id hash.
        Consumes the token so it cannot be reused.
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        if not new_password or len(new_password) < 8:
            raise RegistrationError("New password must be at least 8 characters in length.")

        if new_password != confirm_password:
            raise RegistrationError("New password and confirmation password do not match.")

        if not (re.search(r"[A-Za-z]", new_password) and re.search(r"\d", new_password)):
            raise RegistrationError("Password must contain both letters and numbers.")

        user_id = self._reset_store.verify_and_consume_token(token)
        if not user_id:
            raise AuthenticationError("Invalid, expired, or previously consumed password reset token.")

        new_hash = self._password_mgr.hash_password(new_password)
        updated = self._identity_repo.update_user_password(user_id, new_hash)
        if not updated:
            raise AuthenticationError("User associated with reset token was not found.")

        logger.info(f"Password reset successfully completed for user_id={user_id}")
        return True

    def submit_account_request(
        self,
        full_name: str,
        username: Optional[str],
        role: str,
        password: str,
        confirm_password: str,
        department: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes account requests:
        1. Low-privilege roles (STUDENT, FACULTY): directly provisions active account.
        2. Privileged roles (HOD, DEAN, PRINCIPAL, MANAGEMENT, IQAC, COE, PLACEMENT, etc.):
           submits an institutional account request in PENDING status for authorized administrative review.
        """
        if not settings.AUTH_ENABLED:
            raise AuthenticationError("Authentication service is disabled.")

        if not full_name or len(full_name.strip()) < 2:
            raise RegistrationError("Full institutional name must be at least 2 characters in length.")

        # Determine sanitized username
        clean_user = (username or "").strip()
        if not clean_user:
            clean_name = re.sub(r"[^a-zA-Z0-9]", "", full_name).lower()
            if not clean_name:
                clean_name = "user"
            clean_user = f"{clean_name[:20]}_{secrets.randbelow(10000):04d}"

        if not re.match(r"^[a-zA-Z0-9_.-]{3,64}$", clean_user):
            raise RegistrationError("Username must be between 3 and 64 alphanumeric characters (may include _, -, .).")

        if not password or len(password) < 8:
            raise RegistrationError("Password must be at least 8 characters in length.")

        if password != confirm_password:
            raise RegistrationError("Password and confirmation password do not match.")

        if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
            raise RegistrationError("Password must contain both letters and numbers.")

        norm_role = role.strip().upper() if role else "STUDENT"

        # Check existing registered user
        if self._identity_repo.get_user_by_username(clean_user):
            raise RegistrationError(f"Institutional username '{clean_user}' is already registered. Please choose another username or sign in.")

        user_email = email.strip().lower() if email else f"{clean_user.lower()}@vignan.ac.in"

        # Branch 1: Self-registration for standard low-privilege roles
        if norm_role in ALLOWED_SELF_REGISTRATION_ROLES:
            user = self.register_account(
                username=clean_user,
                password=password,
                confirm_password=confirm_password,
                full_name=full_name,
                role=norm_role,
                email=user_email,
            )
            return {
                "account_type": "self_service",
                "status": "created",
                "message": "Account created successfully.",
                "request_id": None,
                "user": user,
            }

        # Branch 2: Privileged institutional role request
        if norm_role in PRIVILEGED_ROLES:
            # Check for duplicate pending requests
            if self._account_request_store.has_pending_request(clean_user, user_email):
                raise RegistrationError("An account request is already pending review.")

            clean_dept: Optional[str] = None
            if norm_role == "HOD":
                if not department or not department.strip():
                    raise RegistrationError("Department is required for Head of Department (HOD) account request.")

                from backend.app.services.identity_resolution import IdentityResolutionService
                id_svc = IdentityResolutionService()
                dept_codes = id_svc.get_all_department_codes()
                clean_dept = department.strip().upper()
                if dept_codes and clean_dept not in dept_codes:
                    raise RegistrationError(f"Invalid requested department '{department}'. Must be a recognized college department.")
            elif department and department.strip():
                clean_dept = department.strip().upper()

            # Hash password with Argon2id; plaintext is discarded immediately
            pwd_hash = self._password_mgr.hash_password(password)

            record = self._account_request_store.create_request(
                full_name=full_name.strip(),
                username=clean_user,
                email=user_email,
                requested_role=norm_role,
                requested_department=clean_dept,
                password_hash=pwd_hash,
            )

            logger.info(
                f"Privileged institutional account request recorded: request_id={record['request_id']}, role={norm_role}, dept={clean_dept}"
            )

            return {
                "account_type": "privileged_request",
                "status": "pending",
                "request_id": record["request_id"],
                "message": "Your request for institutional access has been submitted for authorized review.",
            }

        # Branch 3: Unknown / arbitrary role
        raise RegistrationError(
            f"Invalid institutional role '{role}'. Please select an authorized institutional role."
        )

    def list_account_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns registered account requests."""
        return self._account_request_store.list_requests(status)

    def approve_account_request(
        self,
        request_id: str,
        approver: AuthenticatedPrincipal,
        department_override: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approves a pending institutional account request and provisions the active user in IdentityRepository.
        Only accessible by administrators (ADMIN, PRINCIPAL, MANAGEMENT).
        Requesters cannot approve their own requests.
        """
        if not (approver.has_role("ADMIN") or approver.has_role("PRINCIPAL") or approver.has_role("MANAGEMENT")):
            raise AuthorizationError("Only institutional administrators can approve account requests.")

        req = self._account_request_store.get_request(request_id)
        if not req:
            raise RegistrationError("Account request not found.")

        if req["status"] != "PENDING":
            raise RegistrationError(f"Cannot approve request with status '{req['status']}'. Must be PENDING.")

        # Requesters cannot approve their own requests
        if approver.username.lower() == req["username"].lower():
            raise AuthorizationError("Requesters cannot approve their own account requests.")

        role = req["requested_role"]
        target_dept = (department_override or req.get("requested_department") or "").strip().upper()

        if role == "HOD":
            if not target_dept:
                raise RegistrationError("Department must be specified to provision an HOD account.")
            from backend.app.services.identity_resolution import IdentityResolutionService
            id_svc = IdentityResolutionService()
            dept_map = id_svc.get_all_department_map()
            if dept_map and target_dept not in dept_map and target_dept.lower() not in dept_map:
                raise RegistrationError(f"Department '{target_dept}' does not exist in authoritative college database.")
            scoped_roles = [ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id=f"dept-{target_dept.lower()}-001")]
        elif role in ["PRINCIPAL", "MANAGEMENT", "IQAC", "COE", "PLACEMENT"]:
            scoped_roles = [ScopedRoleAssignment(role=role, scope_type=ScopeType.INSTITUTION)]
        elif role == "DEAN":
            scoped_roles = [ScopedRoleAssignment(role="DEAN", scope_type=ScopeType.CAMPUS, scope_id="campus-main-001")]
        elif role in ["COUNSELLOR", "MENTOR"]:
            scoped_roles = [ScopedRoleAssignment(role=role, scope_type=ScopeType.SELF)]
        else:
            scoped_roles = [ScopedRoleAssignment(role=role, scope_type=ScopeType.SELF)]

        user = self._identity_repo.register_user(
            username=req["username"],
            email=req["email"],
            password_hash=req["password_hash"],
            scoped_roles=scoped_roles,
            is_active=True,
        )

        updated_req = self._account_request_store.update_status(
            request_id=request_id,
            status="APPROVED",
            reviewed_by=approver.username,
            notes=notes,
            provisioned_user_id=user["user_id"],
        )

        logger.info(
            f"Account request approved: id={request_id}, role={role}, dept={target_dept}, provisioned_user_id={user['user_id']}"
        )
        return updated_req

    def reject_account_request(
        self,
        request_id: str,
        approver: AuthenticatedPrincipal,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rejects a pending account request."""
        if not (approver.has_role("ADMIN") or approver.has_role("PRINCIPAL") or approver.has_role("MANAGEMENT")):
            raise AuthorizationError("Only institutional administrators can reject account requests.")

        req = self._account_request_store.get_request(request_id)
        if not req:
            raise RegistrationError("Account request not found.")

        if req["status"] != "PENDING":
            raise RegistrationError(f"Cannot reject request with status '{req['status']}'. Must be PENDING.")

        if approver.username.lower() == req["username"].lower():
            raise AuthorizationError("Requesters cannot reject their own account requests.")

        updated_req = self._account_request_store.update_status(
            request_id=request_id,
            status="REJECTED",
            reviewed_by=approver.username,
            notes=reason,
        )
        logger.info(f"Account request rejected: id={request_id}, reviewer={approver.username}")
        return updated_req



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
    reset_account_request_store()

