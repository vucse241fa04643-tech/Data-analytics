"""
Agent 63 – Security Foundation & Architectural Boundary
Defines abstract types and domain interfaces for future authentication and RBAC.

CRITICAL PHASE 2 BOUNDARY:
- Authentication (JWT / sessions / passwords) is NOT implemented in Phase 2.
- RBAC enforcement is NOT implemented in Phase 2.
- No mock credentials, fake users, or admin bypasses exist.
- Institutional endpoints remain non-existent in Phase 2.

Future Pipeline Architecture:
Request
  ↓
Authentication (Verify credentials / identity)
  ↓
Principal (Extracted user identity & institutional attributes)
  ↓
RBAC & Permission Check (Verify role authority for domain/intent)
  ↓
Scope (Departmental / faculty / section boundaries)
  ↓
Intent Authorization (Is the semantic query permissible for this role?)
  ↓
Schema Registry (Are queried tables/views classified under allowed access?)
  ↓
Safe SQL Generation (Read-only, parameterized, policy-enforced)
  ↓
Database Execution (Dedicated read-only Postgres role)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set


class InstitutionalRole(str, Enum):
    """
    Recognized institutional roles based on Agent 63 domain specifications.
    These define hierarchical and departmental boundaries for Phase 4+.
    """
    GOVERNING_BODY = "GOVERNING_BODY"
    PRINCIPAL = "PRINCIPAL"
    VICE_PRINCIPAL = "VICE_PRINCIPAL"
    DEAN_ACADEMICS = "DEAN_ACADEMICS"
    DEAN_STUDENT_AFFAIRS = "DEAN_STUDENT_AFFAIRS"
    CONTROLLER_OF_EXAMINATIONS = "CONTROLLER_OF_EXAMINATIONS"
    HEAD_OF_DEPARTMENT = "HEAD_OF_DEPARTMENT"
    FACULTY = "FACULTY"
    CLASS_TEACHER = "CLASS_TEACHER"
    ACADEMIC_ADVISOR = "ACADEMIC_ADVISOR"
    ACCOUNTS_OFFICER = "ACCOUNTS_OFFICER"
    LIBRARIAN = "LIBRARIAN"
    HOSTEL_WARDEN = "HOSTEL_WARDEN"
    TRAINING_PLACEMENT_OFFICER = "TRAINING_PLACEMENT_OFFICER"
    COUNSELLOR = "COUNSELLOR"  # Protected domain (health_counselling)
    HR_ADMIN = "HR_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    AUDITOR = "AUDITOR"


@dataclass(frozen=True)
class Principal:
    """
    Represents an authenticated institutional identity.
    Placeholder structure for Phase 4 authentication integration.
    """
    user_id: str
    username: str
    roles: Set[InstitutionalRole] = field(default_factory=set)
    department_id: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True


@dataclass(frozen=True)
class AuthorizationDecision:
    """
    Represents the outcome of a semantic or data-access authorization check.
    Placeholder structure for future query policy evaluation.
    """
    allowed: bool
    reason: str
    required_role: Optional[InstitutionalRole] = None
    applied_scope_filter: Optional[str] = None
