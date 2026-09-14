"""
Agent 63 – Authentication API Schemas & DTOs
Safe request and response data transfer objects for authentication endpoints.
Excludes sensitive attributes, secrets, and raw password hashes.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credential login payload submitted by institutional users."""
    username: str = Field(..., min_length=3, max_length=128, description="Institutional username or roll number")
    password: str = Field(..., min_length=6, max_length=256, description="Plaintext password for verification")


class TokenResponse(BaseModel):
    """Safe bearer token response issued upon successful authentication."""
    access_token: str = Field(..., description="Signed cryptographically verified JWT bearer token")
    token_type: str = Field("bearer", description="Standard OAuth2 token type")
    expires_in: int = Field(..., description="Access token lifespan in seconds")


class UserProfileResponse(BaseModel):
    """
    Sanitized representation of the currently authenticated principal.
    Strictly excludes password hashes, database credentials, and internal secrets.
    """
    user_id: str = Field(..., description="User unique identifier")
    username: str = Field(..., description="Institutional username")
    email: str = Field(..., description="Institutional email address")
    is_active: bool = Field(..., description="Account active status")
    roles: List[str] = Field(default_factory=list, description="Assigned institutional roles")
    scoped_roles: List[Dict[str, Any]] = Field(default_factory=list, description="Scope boundaries")
    permissions: List[str] = Field(default_factory=list, description="Authorized analytics permissions")


class LogoutResponse(BaseModel):
    """Acknowledgment response for token revocation/logout."""
    message: str = Field("Logout successful. Token revoked.", description="Status message")
    revoked: bool = Field(True, description="Whether token revocation was registered")


class SignUpRequest(BaseModel):
    """Self-service registration payload."""
    username: str = Field(..., min_length=3, max_length=64, description="Desired institutional username")
    password: str = Field(..., min_length=8, max_length=256, description="Account password (min 8 characters)")
    confirm_password: str = Field(..., min_length=8, max_length=256, description="Password confirmation")


class CreateAccountRequest(BaseModel):
    """Institutional account creation payload with role selection."""
    full_name: str = Field(..., min_length=2, max_length=128, description="Full institutional name")
    username: Optional[str] = Field(None, min_length=3, max_length=64, description="Optional username (derived from name if omitted)")
    email: Optional[str] = Field(None, max_length=128, description="Institutional email address")
    role: str = Field(..., min_length=2, max_length=64, description="Selected institutional role")
    department: Optional[str] = Field(None, max_length=64, description="Requested department code (for HOD)")
    password: str = Field(..., min_length=8, max_length=256, description="Account password (min 8 characters)")
    confirm_password: str = Field(..., min_length=8, max_length=256, description="Password confirmation")


class ForgotPasswordRequest(BaseModel):
    """Password reset request payload."""
    identifier: str = Field(..., min_length=3, max_length=128, description="Institutional username or registered email")


class ResetPasswordRequest(BaseModel):
    """Password reset confirmation payload."""
    token: str = Field(..., min_length=16, max_length=256, description="Single-use password reset token")
    new_password: str = Field(..., min_length=8, max_length=256, description="New account password")
    confirm_password: str = Field(..., min_length=8, max_length=256, description="New password confirmation")


class MessageResponse(BaseModel):
    """Sanitized generic status acknowledgment."""
    message: str = Field(..., description="Human-readable outcome message")
    status: str = Field("success", description="Status code identifier")
    request_id: Optional[str] = Field(None, description="Identifier of created request if applicable")
    account_type: Optional[str] = Field(None, description="Account creation type: self_service or privileged_request")


class DepartmentItemResponse(BaseModel):
    """Authoritative department item from college database."""
    code: str = Field(..., description="Department uppercase code (e.g. CSE)")
    name: str = Field(..., description="Department descriptive name")
    department_id: str = Field(..., description="Relational department UUID")


class AccountRequestRecordResponse(BaseModel):
    """Representation of an institutional account request."""
    request_id: str = Field(..., description="Unique request identifier")
    full_name: str = Field(..., description="Requester full name")
    username: str = Field(..., description="Requested username")
    email: str = Field(..., description="Requester email")
    requested_role: str = Field(..., description="Requested institutional role")
    requested_department: Optional[str] = Field(None, description="Requested department code")
    status: str = Field(..., description="Request state: PENDING, APPROVED, REJECTED, ACTIVE")
    created_at: str = Field(..., description="ISO creation timestamp")
    reviewed_by: Optional[str] = Field(None, description="Reviewing administrator username")
    reviewed_at: Optional[str] = Field(None, description="ISO review timestamp")


class AccountRequestApproval(BaseModel):
    """Payload for approving an account request."""
    department_override: Optional[str] = Field(None, description="Authoritative department override")
    notes: Optional[str] = Field(None, description="Administrative audit notes")


class AccountRequestRejection(BaseModel):
    """Payload for rejecting an account request."""
    reason: Optional[str] = Field(None, description="Administrative justification")
