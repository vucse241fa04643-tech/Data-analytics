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
