"""
Agent 63 – FastAPI Authentication & Authorization Dependencies
Provides reusable dependencies for route security, principal extraction,
role/permission gatekeeping, and scope enforcement.
"""

from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError, AuthorizationError
from backend.app.core.logging import get_logger, request_id_ctx_var
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType
from backend.app.services.audit import AuditAction, AuthAuditEvent, get_audit_service
from backend.app.services.authentication import AuthenticationService, get_authentication_service
from backend.app.services.authorization import AuthorizationService, get_authorization_service

logger = get_logger("agent63.dependencies.auth")


def extract_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Extracts raw JWT bearer token from standard Authorization header."""
    if not authorization:
        raise AuthenticationError("Authorization header is missing.")

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format. Expected 'Bearer <token>'.")

    return parts[1]


def get_current_principal(
    request: Request,
    token: str = Depends(extract_bearer_token),
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> AuthenticatedPrincipal:
    """
    Extracts, cryptographically validates, and resolves the current AuthenticatedPrincipal.
    CRITICAL SECURITY RULES:
    1. Client-supplied headers like X-Role, X-User-Role, or X-Department-ID are strictly ignored.
    2. Role claims are resolved server-side from current trusted identity state.
    3. Inactive or disabled accounts are immediately rejected with HTTP 401.
    """
    if not settings.AUTH_ENABLED:
        logger.warning("Attempted access to protected endpoint while AUTH_ENABLED is False. Failing closed.")
        raise AuthenticationError("Authentication is disabled or unconfigured; protected endpoints cannot be accessed.")

    # Defensive audit: log and ignore any attempt to inject client role headers
    for forged_header in ["x-role", "x-user-role", "x-department-id", "x-scope"]:
        if forged_header in request.headers:
            logger.info(
                f"Defensive notice: Client attempted to pass unverified {forged_header} header. "
                "Header discarded; authorization is strictly derived server-side."
            )

    principal = auth_service.get_principal_from_token(token)
    if not principal.is_active:
        raise AuthenticationError("Account is inactive or disabled.")

    return principal


def require_roles(*roles: str) -> Callable[..., AuthenticatedPrincipal]:
    """Dependency factory that restricts endpoint access to users holding at least one specified role."""
    def _role_checker(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
        audit_service = Depends(get_audit_service),
    ) -> AuthenticatedPrincipal:
        if not principal.has_any_role(*roles):
            audit_service.log_event(
                AuthAuditEvent(
                    action=AuditAction.AUTHORIZATION_DENIAL,
                    actor_user_id=principal.user_id,
                    actor_username=principal.username,
                    actor_role=",".join(principal.roles),
                    reason=f"Missing required role. Required one of: {roles}",
                )
            )
            raise AuthorizationError("Access denied: User does not possess the required institutional role.")
        return principal

    return _role_checker


def require_permissions(*permissions: str) -> Callable[..., AuthenticatedPrincipal]:
    """Dependency factory that restricts endpoint access to users holding at least one specified permission."""
    def _permission_checker(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
        audit_service = Depends(get_audit_service),
    ) -> AuthenticatedPrincipal:
        if not principal.has_any_permission(*permissions):
            audit_service.log_event(
                AuthAuditEvent(
                    action=AuditAction.AUTHORIZATION_DENIAL,
                    actor_user_id=principal.user_id,
                    actor_username=principal.username,
                    actor_role=",".join(principal.roles),
                    reason=f"Missing required permission. Required one of: {permissions}",
                )
            )
            raise AuthorizationError("Access denied: Insufficient permissions for this resource.")
        return principal

    return _permission_checker


def require_department_scope(
    department_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    authz_service: AuthorizationService = Depends(get_authorization_service),
    audit_service = Depends(get_audit_service),
) -> AuthenticatedPrincipal:
    """Enforces that the requested department_id falls within the principal's authorized scope."""
    decision = authz_service.authorize_action(
        principal=principal,
        scope_type=ScopeType.DEPARTMENT,
        scope_id=department_id,
    )
    if not decision.allowed:
        audit_service.log_event(
            AuthAuditEvent(
                action=AuditAction.PRIVILEGE_ESCALATION_ATTEMPT,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                actor_role=",".join(principal.roles),
                resource=f"department:{department_id}",
                reason="Departmental scope boundary violation.",
            )
        )
        raise AuthorizationError("Access denied: Requested department is outside your authorized scope.")
    return principal
