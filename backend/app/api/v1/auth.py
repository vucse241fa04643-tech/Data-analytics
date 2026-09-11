"""
Agent 63 – Authentication API Endpoints
Provides secure login, current profile inspection, and stateful token logout.
Returns safe payloads only; never leaks password hashes or credentials.
"""

from fastapi import APIRouter, Depends, Request, status

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError
from backend.app.dependencies.auth import extract_bearer_token, get_current_principal
from backend.app.schemas.auth import LoginRequest, LogoutResponse, TokenResponse, UserProfileResponse
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.audit import AuditAction, AuthAuditEvent, get_audit_service
from backend.app.services.authentication import AuthenticationService, get_authentication_service

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate institutional user")
def login(
    payload: LoginRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> TokenResponse:
    """
    Authenticates user credentials against institutional identity records using Argon2id.
    Returns a cryptographically signed JWT bearer token on success.
    Fails safely without disclosing account existence.
    """
    if not settings.AUTH_ENABLED:
        raise AuthenticationError("Authentication service is currently disabled.")

    principal = auth_service.authenticate_user(payload.username, payload.password)
    if not principal:
        audit_service.log_event(
            AuthAuditEvent(
                action=AuditAction.LOGIN_FAILURE,
                actor_username=payload.username,
                reason="Invalid credentials or unknown username",
            )
        )
        raise AuthenticationError("Invalid username or password.")

    token, expires_in, _ = auth_service.create_access_token(principal)

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            actor_user_id=principal.user_id,
            actor_username=principal.username,
            actor_role=",".join(principal.roles),
            reason="Authenticated with valid credentials",
        )
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserProfileResponse, summary="Retrieve authenticated user profile")
def get_me(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UserProfileResponse:
    """
    Returns sanitized current user identity, active status, roles, scopes, and permissions.
    Strictly excludes password hashes, database credentials, or secret keys.
    """
    return UserProfileResponse(
        user_id=principal.user_id,
        username=principal.username,
        email=principal.email,
        is_active=principal.is_active,
        roles=principal.roles,
        scoped_roles=[sr.model_dump() for sr in principal.scoped_roles],
        permissions=sorted(list(principal.permissions)),
    )


@router.post("/logout", response_model=LogoutResponse, summary="Revoke token and logout")
def logout(
    token: str = Depends(extract_bearer_token),
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> LogoutResponse:
    """
    Revokes the current JWT bearer token via its JTI in the token revocation store.
    Subsequent API requests presenting the revoked token will be rejected with HTTP 401.
    """
    if not settings.AUTH_ENABLED:
        raise AuthenticationError("Authentication service is currently disabled.")

    revoked = auth_service.logout_token(token)

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGOUT,
            reason="Token JTI registered in revocation store",
        )
    )

    return LogoutResponse(
        message="Logout successful. Token revoked.",
        revoked=revoked,
    )
