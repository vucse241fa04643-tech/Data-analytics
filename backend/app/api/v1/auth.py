"""
Agent 63 – Authentication API Endpoints
Provides secure login, current profile inspection, and stateful token logout.
Returns safe payloads only; never leaks password hashes or credentials.
"""

from fastapi import APIRouter, Depends, Request, status

from backend.app.core.config import settings
from typing import List, Optional
import re
import secrets

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError, AuthorizationError, RegistrationError
from backend.app.dependencies.auth import extract_bearer_token, get_current_principal
from backend.app.schemas.auth import (
    AccountRequestApproval,
    AccountRequestRecordResponse,
    AccountRequestRejection,
    CreateAccountRequest,
    DepartmentItemResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    ResetPasswordRequest,
    SignUpRequest,
    TokenResponse,
    UserProfileResponse,
)
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.audit import AuditAction, AuthAuditEvent, get_audit_service
from backend.app.services.authentication import AuthenticationService, get_authentication_service

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.get("/departments", response_model=List[DepartmentItemResponse], summary="List authoritative college departments")
def list_departments() -> List[DepartmentItemResponse]:
    """
    Retrieves authoritative department identifiers dynamically from PostgreSQL core.department.
    Never exposes internal database credentials or SQL. Zero hardcoding.
    """
    from backend.app.services.identity_resolution import IdentityResolutionService
    id_svc = IdentityResolutionService()
    depts = id_svc.get_all_departments()
    return [
        DepartmentItemResponse(
            code=d["code"],
            name=d["name"],
            department_id=str(d["department_id"]),
        )
        for d in depts
    ]


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


@router.post("/signup", response_model=MessageResponse, summary="Self-service institutional registration")
def signup(
    payload: SignUpRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Registers a new standard institutional account (default role: STUDENT).
    Validates password strength, prevents duplicate usernames, and uses Argon2id hashing.
    """
    user = auth_service.register_account(
        username=payload.username,
        password=payload.password,
        confirm_password=payload.confirm_password,
        role="STUDENT",
    )

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            actor_user_id=user["user_id"],
            actor_username=user["username"],
            actor_role="STUDENT",
            reason="Institutional self-registration",
        )
    )

    return MessageResponse(
        message="Account created successfully.",
        status="success",
        account_type="self_service",
    )


@router.post("/create-account", response_model=MessageResponse, summary="Create institutional account or submit privileged access request")
def create_account(
    payload: CreateAccountRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Creates an institutional account or submits a privileged access request.
    - Low-privilege roles (Student, Faculty): creates account directly.
    - Privileged roles (HOD, Dean, Principal, Management, IQAC, COE, Placement, Counsellor/Mentor):
      records an institutional account request in PENDING status for authorized administrative review.
      Never auto-assigns privileged roles or issues privileged JWT tokens.
    """
    result = auth_service.submit_account_request(
        full_name=payload.full_name,
        username=payload.username,
        role=payload.role,
        password=payload.password,
        confirm_password=payload.confirm_password,
        department=payload.department,
        email=payload.email,
    )

    if result["account_type"] == "self_service":
        audit_service.log_event(
            AuthAuditEvent(
                action=AuditAction.LOGIN_SUCCESS,
                actor_username=payload.username or payload.full_name,
                actor_role=payload.role.strip().upper(),
                reason="Institutional self-registration",
            )
        )
    else:
        audit_service.log_event(
            AuthAuditEvent(
                action=AuditAction.LOGIN_FAILURE,
                actor_username=payload.username or payload.full_name,
                actor_role=payload.role.strip().upper(),
                reason="Privileged institutional account request submitted for review",
            )
        )

    return MessageResponse(
        message=result["message"],
        status=result["status"],
        request_id=result.get("request_id"),
        account_type=result["account_type"],
    )


@router.get("/account-requests", response_model=List[AccountRequestRecordResponse], summary="List institutional account requests")
def list_account_requests(
    status: Optional[str] = None,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> List[AccountRequestRecordResponse]:
    """
    Lists institutional account requests. Restricted to administrators (ADMIN, PRINCIPAL, MANAGEMENT).
    """
    if not (principal.has_role("ADMIN") or principal.has_role("PRINCIPAL") or principal.has_role("MANAGEMENT")):
        raise AuthorizationError("Access denied: administrator authority required to view account requests.")

    reqs = auth_service.list_account_requests(status)
    return [
        AccountRequestRecordResponse(
            request_id=r["request_id"],
            full_name=r["full_name"],
            username=r["username"],
            email=r["email"],
            requested_role=r["requested_role"],
            requested_department=r.get("requested_department"),
            status=r["status"],
            created_at=r["created_at"],
            reviewed_by=r.get("reviewed_by"),
            reviewed_at=r.get("reviewed_at"),
        )
        for r in reqs
    ]


@router.post("/account-requests/{request_id}/approve", response_model=MessageResponse, summary="Approve privileged account request")
def approve_account_request(
    request_id: str,
    payload: AccountRequestApproval = AccountRequestApproval(),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Approves an account request and provisions the active user in the identity repository with authorized role and scope.
    Restricted to administrators. Requesters cannot approve their own requests.
    """
    updated = auth_service.approve_account_request(
        request_id=request_id,
        approver=principal,
        department_override=payload.department_override,
        notes=payload.notes,
    )

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            actor_username=principal.username,
            reason=f"Approved account request {request_id} for user {updated['username']}",
        )
    )

    return MessageResponse(
        message=f"Account request for '{updated['username']}' approved and provisioned as {updated['requested_role']}.",
        status="approved",
        request_id=request_id,
    )


@router.post("/account-requests/{request_id}/reject", response_model=MessageResponse, summary="Reject privileged account request")
def reject_account_request(
    request_id: str,
    payload: AccountRequestRejection = AccountRequestRejection(),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Rejects an account request. Restricted to administrators.
    """
    updated = auth_service.reject_account_request(
        request_id=request_id,
        approver=principal,
        reason=payload.reason,
    )

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.AUTHORIZATION_DENIAL,
            actor_username=principal.username,
            reason=f"Rejected account request {request_id} for user {updated['username']}",
        )
    )

    return MessageResponse(
        message=f"Account request for '{updated['username']}' rejected.",
        status="rejected",
        request_id=request_id,
    )



@router.post("/forgot-password", response_model=MessageResponse, summary="Initiate password recovery")
def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Initiates enumeration-resistant password reset request.
    Always returns identical safe response regardless of identifier existence.
    """
    auth_service.request_password_reset(payload.identifier)

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGIN_FAILURE,
            actor_username=payload.identifier,
            reason="Password reset requested",
        )
    )

    return MessageResponse(
        message="Password reset request submitted. If an authorized institutional account matches the provided identifier, your administrator or departmental security office has logged the recovery request.",
        status="submitted",
    )


@router.post("/reset-password", response_model=MessageResponse, summary="Confirm password reset with token")
def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
    audit_service = Depends(get_audit_service),
) -> MessageResponse:
    """
    Validates single-use reset token, hashes new password with Argon2id,
    and updates institutional user credentials.
    """
    auth_service.reset_password_with_token(
        token=payload.token,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )

    audit_service.log_event(
        AuthAuditEvent(
            action=AuditAction.LOGIN_SUCCESS,
            reason="Password reset successfully completed with verified single-use token",
        )
    )

    return MessageResponse(
        message="Password reset successfully. You may now sign in with your new password.",
        status="success",
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
