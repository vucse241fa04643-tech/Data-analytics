"""
Agent 63 – Authenticated Principal & Authorization Domain Models
Defines internal representations of authenticated identity, scoped roles,
and permission sets derived from the authoritative college identity schema (identity.*).
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class ScopeType(str, Enum):
    """
    Scope tiers matching the check constraint in identity.user_role:
    CHECK (scope_type IN ('SELF','SECTION','COURSE_OFFERING','PROGRAMME','DEPARTMENT','CAMPUS','INSTITUTION'))
    """
    SELF = "SELF"
    SECTION = "SECTION"
    COURSE_OFFERING = "COURSE_OFFERING"
    PROGRAMME = "PROGRAMME"
    DEPARTMENT = "DEPARTMENT"
    CAMPUS = "CAMPUS"
    INSTITUTION = "INSTITUTION"


class ScopedRoleAssignment(BaseModel):
    """Represents a role granted within an explicit organizational scope boundary."""
    role: str = Field(..., description="Role code, e.g. HOD, FACULTY, STUDENT, PRINCIPAL")
    scope_type: ScopeType = Field(..., description="Organizational boundary tier")
    scope_id: Optional[str] = Field(None, description="UUID of target scope entity (null for SELF/INSTITUTION)")

    def matches(self, target_scope_type: ScopeType, target_scope_id: Optional[str] = None) -> bool:
        """Evaluates whether this scoped assignment encompasses the requested scope."""
        # Institution-wide scope encompasses all lower scopes
        if self.scope_type == ScopeType.INSTITUTION:
            return True
        if self.scope_type == target_scope_type:
            if self.scope_id is None or target_scope_id is None:
                return True
            return str(self.scope_id).lower() == str(target_scope_id).lower()
        return False


class AuthenticatedPrincipal(BaseModel):
    """
    Internal security principal representing the verified user identity,
    resolved server-side from identity.app_user and identity.user_role.
    Never exposed directly in raw form to external API clients.
    """
    user_id: str = Field(..., description="Unique UUID of identity.app_user")
    username: str = Field(..., description="Institutional login handle")
    email: str = Field(..., description="Institutional email address")
    person_id: Optional[str] = Field(None, description="Linked people.person UUID if human user")
    is_active: bool = Field(True, description="Account active status")
    is_service_account: bool = Field(False, description="Whether identity is a background worker")
    roles: List[str] = Field(default_factory=list, description="List of role codes held by user")
    scoped_roles: List[ScopedRoleAssignment] = Field(default_factory=list, description="Scoped role bindings")
    permissions: Set[str] = Field(default_factory=set, description="Set of resolved action permissions")

    def has_role(self, role_code: str) -> bool:
        """Checks if principal holds the specified role."""
        return role_code.upper() in [r.upper() for r in self.roles]

    def has_any_role(self, *role_codes: str) -> bool:
        """Checks if principal holds at least one of the specified roles."""
        user_roles = {r.upper() for r in self.roles}
        target_roles = {r.upper() for r in role_codes}
        return bool(user_roles & target_roles)

    def has_permission(self, permission_code: str) -> bool:
        """Checks if principal possesses the specified permission."""
        return permission_code.lower() in {p.lower() for p in self.permissions}

    def has_any_permission(self, *permission_codes: str) -> bool:
        """Checks if principal possesses at least one of the specified permissions."""
        user_perms = {p.lower() for p in self.permissions}
        target_perms = {p.lower() for p in permission_codes}
        return bool(user_perms & target_perms)

    def get_scopes_for_role(self, role_code: str) -> List[ScopedRoleAssignment]:
        """Returns all scoped bindings for a specific role."""
        return [sr for sr in self.scoped_roles if sr.role.upper() == role_code.upper()]

    def is_in_scope(self, scope_type: ScopeType, target_scope_id: Optional[str] = None) -> bool:
        """Verifies whether any of the principal's active roles covers the requested scope."""
        for sr in self.scoped_roles:
            if sr.matches(scope_type, target_scope_id):
                return True
        return False
