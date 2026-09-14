"""
Agent 63 – Authorization Service & Policy Engine
Implements multi-tiered, server-side RBAC and scoped authorization:
authenticated principal -> role -> permission -> scope -> semantic sensitivity -> authorization decision.
Integrates with Phase 4 Semantic Layer (semantic_registry.json and semantic_security.json).
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)

logger = get_logger("agent63.services.authorization")

# Mapping of semantic domains to required base permissions
DOMAIN_PERMISSION_MAP: Dict[str, str] = {
    "attendance": "attendance.read",
    "assessment": "assessment.read",
    "outcomes": "outcomes.read",
    "placement": "placement.read",
    "academics": "academics.read",
    "quality": "quality.read",
}

STRICTLY_DENIED_PREFIXES: List[str] = [
    "confidential.",
    "assessment.question_paper",
    "exams.question_paper_delivery",
    "exams.malpractice_incident",
    "identity.credential",
    "identity.auth_token",
]


class AuthorizationDecision(BaseModel):
    """
    Internal structured explanation of an authorization evaluation.
    Detailed reason codes are retained for internal logging and tests,
    while external clients receive safe generic HTTP 403 responses.
    """
    allowed: bool
    reason_code: str = Field(
        ...,
        description=(
            "AUTHORIZED | UNAUTHENTICATED | INACTIVE_ACCOUNT | INSUFFICIENT_PERMISSIONS | "
            "ROLE_NOT_ASSIGNED | SCOPE_OUT_OF_BOUNDS | SENSITIVITY_DENIED | "
            "RESTRICTED_RESOURCE | METRIC_NOT_FOUND | METRIC_UNAPPROVED"
        ),
    )
    metric_id: Optional[str] = None
    required_permission: Optional[str] = None
    effective_scope: Dict[str, Any] = Field(default_factory=dict)
    message: str = "Access permitted"


class AuthorizationService:
    """Centralized authorization engine for Agent 63."""

    def __init__(self, semantic_registry: Optional[SemanticRegistryService] = None):
        self._semantic_registry = semantic_registry or get_semantic_registry_service()

    def authorize_action(
        self,
        principal: Optional[AuthenticatedPrincipal],
        required_permission: Optional[str] = None,
        required_role: Optional[str] = None,
        scope_type: Optional[ScopeType] = None,
        scope_id: Optional[str] = None,
    ) -> AuthorizationDecision:
        """
        Evaluates whether a principal is authorized to perform a general action
        given a required permission, role, and organizational scope boundary.
        """
        if principal is None:
            return AuthorizationDecision(
                allowed=False,
                reason_code="UNAUTHENTICATED",
                message="Authentication required.",
            )

        if not principal.is_active:
            return AuthorizationDecision(
                allowed=False,
                reason_code="INACTIVE_ACCOUNT",
                message="Account is inactive or disabled.",
            )

        # 1. Role verification
        if required_role and not principal.has_role(required_role):
            logger.info(
                f"Authorization denied for user {principal.username}: missing required role {required_role}"
            )
            return AuthorizationDecision(
                allowed=False,
                reason_code="ROLE_NOT_ASSIGNED",
                message=f"Missing required institutional role.",
            )

        # 2. Permission verification
        if required_permission and not principal.has_permission(required_permission):
            logger.info(
                f"Authorization denied for user {principal.username}: missing permission {required_permission}"
            )
            return AuthorizationDecision(
                allowed=False,
                reason_code="INSUFFICIENT_PERMISSIONS",
                required_permission=required_permission,
                message="Insufficient permissions for this resource.",
            )

        # 3. Scope boundary verification
        if scope_type:
            if not principal.is_in_scope(scope_type, scope_id):
                logger.info(
                    f"Authorization denied for user {principal.username}: requested scope {scope_type.value} "
                    f"id={scope_id} is outside user's authorized scope."
                )
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="Requested data is outside authorized organizational scope.",
                )

        return AuthorizationDecision(
            allowed=True,
            reason_code="AUTHORIZED",
            effective_scope={"scope_type": scope_type.value if scope_type else "UNCONSTRAINED", "scope_id": scope_id},
            message="Authorized.",
        )

    def authorize_metric(
        self,
        principal: Optional[AuthenticatedPrincipal],
        metric_id: str,
        requested_scope_type: Optional[ScopeType] = None,
        requested_scope_id: Optional[str] = None,
    ) -> AuthorizationDecision:
        """
        Evaluates whether a principal is authorized to query a specific metric definition
        from the Phase 4 Semantic Layer, considering lifecycle, sensitivity, and scope.
        """
        if principal is None:
            return AuthorizationDecision(
                allowed=False,
                reason_code="UNAUTHENTICATED",
                metric_id=metric_id,
                message="Authentication required.",
            )

        if not principal.is_active:
            return AuthorizationDecision(
                allowed=False,
                reason_code="INACTIVE_ACCOUNT",
                metric_id=metric_id,
                message="Account is inactive.",
            )

        # 1. Resolve metric from semantic registry
        metric = self._semantic_registry.get_metric(metric_id)
        if not metric:
            logger.info(f"Authorization check for unknown metric: {metric_id}")
            return AuthorizationDecision(
                allowed=False,
                reason_code="METRIC_NOT_FOUND",
                metric_id=metric_id,
                message="Metric not found in semantic catalog.",
            )

        # 2. Lifecycle gatekeeping (Only APPROVED metrics eligible for production)
        status = metric.get("status", "DRAFT")
        if status != "APPROVED":
            logger.info(f"Authorization denied for non-approved metric {metric_id} (status={status})")
            return AuthorizationDecision(
                allowed=False,
                reason_code="METRIC_UNAPPROVED",
                metric_id=metric_id,
                message=f"Metric is not approved for production analytics (status={status}).",
            )

        # 3. Check strictly denied prefixes (confidential.*, question papers, etc.)
        for src_obj in metric.get("source_objects", []):
            for prefix in STRICTLY_DENIED_PREFIXES:
                if src_obj.startswith(prefix):
                    logger.info(f"CRITICAL: Metric {metric_id} references denied object {src_obj}")
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="RESTRICTED_RESOURCE",
                        metric_id=metric_id,
                        message="Requested resource is strictly quarantined from institutional analytics.",
                    )

        # 4. Domain permission check
        domain = metric.get("domain", "")
        required_perm = DOMAIN_PERMISSION_MAP.get(domain, f"{domain}.read")
        if not principal.has_permission(required_perm) and not principal.has_permission("analytics.read"):
            logger.info(
                f"Authorization denied: user {principal.username} lacks permission {required_perm} for metric {metric_id}"
            )
            return AuthorizationDecision(
                allowed=False,
                reason_code="INSUFFICIENT_PERMISSIONS",
                metric_id=metric_id,
                required_permission=required_perm,
                message="User does not hold required analytics permission for this domain.",
            )

        # 5. Semantic Sensitivity evaluation
        sensitivity = metric.get("sensitivity", "INTERNAL_INSTITUTIONAL")
        if sensitivity == "RESTRICTED":
            return AuthorizationDecision(
                allowed=False,
                reason_code="SENSITIVITY_DENIED",
                metric_id=metric_id,
                message="Metric sensitivity is RESTRICTED and excluded from general query planning.",
            )

        # 6. Organizational Scope evaluation
        # If user is a student, they can only view self-scoped metrics
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC"):
            # Students can only access SELF scope
            if requested_scope_type is not None and requested_scope_type != ScopeType.SELF:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Student accounts are restricted to self-scoped records.",
                )
            student_valid_ids = {principal.person_id, principal.user_id}
            for sr in principal.get_scopes_for_role("STUDENT"):
                if sr.scope_id:
                    student_valid_ids.add(sr.scope_id)
            student_valid_ids.discard(None)

            if requested_scope_id and requested_scope_id not in student_valid_ids:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Student accounts cannot query another student's records.",
                )

        # If user is an HOD, verify requested department matches their authorized department scope
        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC"):
            hod_scopes = principal.get_scopes_for_role("HOD")
            allowed_dept_ids = {sr.scope_id for sr in hod_scopes if sr.scope_id}
            if requested_scope_type == ScopeType.DEPARTMENT and requested_scope_id:
                if requested_scope_id not in allowed_dept_ids:
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        metric_id=metric_id,
                        message="HOD scope violation: requested department does not match assignment.",
                    )

        # If user is a COUNSELLOR, allow only mentee-scoped attendance and assessment metrics.
        # General institutional analytics remain denied.
        if principal.has_role("COUNSELLOR") and not principal.has_any_role(
            "PRINCIPAL", "HOD", "DEAN", "IQAC", "CAMPUS_ADMIN"
        ):
            counsellor_allowed_domains = {"attendance", "assessment"}
            if domain not in counsellor_allowed_domains:
                logger.info(
                    f"COUNSELLOR {principal.username} denied metric {metric_id}: domain '{domain}' "
                    "is outside counsellor-permitted domains (attendance, assessment)."
                )
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Counsellor accounts are restricted to mentee-scoped attendance and academic metrics.",
                )
            if not principal.person_id:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Counsellor account has no verified faculty identity linkage.",
                )

            # Check for institutional/department scope or targeted individual student
            if requested_scope_type == ScopeType.INSTITUTION:
                if requested_scope_id:
                    # Individual student explicitly targeted
                    from backend.app.services.identity_resolution import get_identity_resolution_service
                    resolver = get_identity_resolution_service()
                    try:
                        counsellor_fac_id = resolver.resolve_counsellor_faculty_id(principal)
                        is_mentee = resolver.is_student_assigned_mentee(counsellor_fac_id, str(requested_scope_id))
                    except Exception:
                        is_mentee = False
                    if not is_mentee:
                        logger.info(
                            f"Counsellor {principal.username} requested student '{requested_scope_id}' outside current mentorship: denied."
                        )
                        return AuthorizationDecision(
                            allowed=False,
                            reason_code="SCOPE_OUT_OF_BOUNDS",
                            metric_id=metric_id,
                            message="You are not authorized to view student records outside your assigned mentee scope.",
                        )
                else:
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        metric_id=metric_id,
                        message="Counsellor accounts cannot query department-level or institution-level scope.",
                    )
            elif requested_scope_type is not None and requested_scope_type != ScopeType.SELF:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Counsellor accounts cannot query department-level or institution-level scope.",
                )

            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                metric_id=metric_id,
                effective_scope={
                    "scope_type": ScopeType.SELF.value,
                    "scope_id": principal.person_id,
                },
                message="Counsellor mentee-scoped metric access authorized.",
            )

        # If requested_scope is explicitly provided, verify principal has matching scope
        if requested_scope_type:
            if not principal.is_in_scope(requested_scope_type, requested_scope_id):
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Requested data scope exceeds principal's authorized boundary.",
                )

        return AuthorizationDecision(
            allowed=True,
            reason_code="AUTHORIZED",
            metric_id=metric_id,
            effective_scope={
                "scope_type": requested_scope_type.value if requested_scope_type else "UNCONSTRAINED",
                "scope_id": requested_scope_id,
            },
            message="Metric access authorized.",
        )

    def authorize_student_list(
        self,
        principal: Optional[AuthenticatedPrincipal],
        student_filters: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationDecision:
        """
        Evaluates whether a principal is authorized to perform student-record retrieval
        under the requested filters and enforces server-side organizational scope.
        """
        if principal is None:
            return AuthorizationDecision(
                allowed=False,
                reason_code="UNAUTHENTICATED",
                message="Authentication required.",
            )

        if not principal.is_active:
            return AuthorizationDecision(
                allowed=False,
                reason_code="INACTIVE_ACCOUNT",
                message="Account is inactive or disabled.",
            )

        from backend.app.services.identity_resolution import get_identity_resolution_service
        id_svc = get_identity_resolution_service()

        filters = student_filters or {}
        user_dept = filters.get("department") or filters.get("department_id") or filters.get("department_code")

        # 1. STUDENT Role: Restricted strictly to own student record (SELF scope)
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC", "FACULTY", "CAMPUS_ADMIN"):
            # If student attempts to query a general department, section, or batch list, deny
            if user_dept or filters.get("section") or filters.get("batch") or filters.get("programme") or filters.get("current_year_of_study"):
                logger.info(f"Student {principal.username} attempted cohort student listing: denied.")
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="You are not authorized to view student records for the requested scope.",
                )

            # Check if student requested another student's ID or roll number
            req_student_id = filters.get("student_id")
            req_roll_no = filters.get("roll_no")
            if req_roll_no:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="You are not authorized to query student records by roll number.",
                )
            if req_student_id and str(req_student_id).upper() != "SELF":
                allowed_self_ids = set()
                if principal.person_id:
                    allowed_self_ids.add(str(principal.person_id).lower())
                for sr in principal.scoped_roles:
                    if sr.scope_type == ScopeType.SELF and sr.scope_id:
                        allowed_self_ids.add(str(sr.scope_id).lower())
                if str(req_student_id).lower() not in allowed_self_ids:
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        message="You are not authorized to view student records for other students.",
                    )

            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                effective_scope={
                    "scope_type": ScopeType.SELF.value,
                    "scope_id": principal.person_id or (
                        principal.scoped_roles[0].scope_id if principal.scoped_roles and principal.scoped_roles[0].scope_type == ScopeType.SELF else None
                    ),
                },
                message="Student self-record access authorized.",
            )

        # 2. HOD Role: Bounded strictly to assigned department scope
        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC", "DEAN", "CAMPUS_ADMIN"):
            hod_dept = id_svc.resolve_hod_department(principal)
            if not hod_dept:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="HOD account has no assigned departmental scope boundary.",
                )
            auth_dept_id, auth_dept_code, auth_dept_name = hod_dept

            if user_dept:
                req_clean = str(user_dept).strip()
                from backend.app.services.sql_compiler import normalize_department_scope
                _, req_code = normalize_department_scope(req_clean)
                if req_code.upper() != auth_dept_code.upper() and req_clean.lower() != auth_dept_name.lower():
                    logger.info(f"HOD {principal.username} requested department '{user_dept}' outside scope: denied.")
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        message="You are not authorized to view student records for the requested scope.",
                    )

            # Cross-department student retrieval check by roll number
            req_roll = filters.get("roll_no")
            if req_roll:
                req_roll_upper = str(req_roll).strip().upper()
                all_codes = id_svc.get_all_department_codes()
                for other_code in all_codes:
                    if other_code != auth_dept_code and other_code in req_roll_upper:
                        logger.info(f"HOD {principal.username} requested foreign roll number '{req_roll}': denied.")
                        return AuthorizationDecision(
                            allowed=False,
                            reason_code="SCOPE_OUT_OF_BOUNDS",
                            message="You are not authorized to view student records for other departments.",
                        )

            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                effective_scope={
                    "scope_type": ScopeType.DEPARTMENT.value,
                    "scope_id": auth_dept_code,
                },
                message="HOD departmental student access authorized.",
            )

        # 3. FACULTY Role: Bounded to assigned department or teaching section
        if principal.has_role("FACULTY") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC", "CAMPUS_ADMIN"):
            fac_scopes = principal.get_scopes_for_role("FACULTY")
            allowed_dept_ids = {sr.scope_id for sr in fac_scopes if sr.scope_type == ScopeType.DEPARTMENT and sr.scope_id}
            dept_map = id_svc.get_all_department_map()
            if user_dept and allowed_dept_ids:
                req_clean = str(user_dept).strip().lower()
                req_norm = dept_map.get(req_clean, str(user_dept).strip().upper())
                matched = any(
                    req_norm == str(d_id).strip() or req_clean == str(d_id).strip().lower()
                    for d_id in allowed_dept_ids
                )
                if not matched:
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        message="You are not authorized to view student records for the requested scope.",
                    )

            primary_scope_id = list(allowed_dept_ids)[0] if allowed_dept_ids else None
            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                effective_scope={
                    "scope_type": ScopeType.DEPARTMENT.value if primary_scope_id else ScopeType.SELF.value,
                    "scope_id": primary_scope_id,
                },
                message="Faculty student access authorized.",
            )

        # 4. COUNSELLOR Role: Bounded strictly to assigned mentees (via studentlife.mentorship)
        # No department, programme, or batch-level queries permitted.
        if principal.has_role("COUNSELLOR") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC", "CAMPUS_ADMIN"):
            if user_dept or filters.get("programme") or filters.get("batch"):
                logger.info(f"Counsellor {principal.username} attempted cohort listing outside mentee scope: denied.")
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="You are not authorized to view student records outside your assigned mentee scope.",
                )
            if not principal.person_id:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="Counsellor account has no verified faculty identity linkage for mentee resolution.",
                )

            # Check if an individual student was targeted
            target_student = filters.get("roll_no") or filters.get("student_id") or filters.get("target_student")
            if target_student and str(target_student).upper() != "SELF":
                from backend.app.services.identity_resolution import get_identity_resolution_service
                resolver = get_identity_resolution_service()
                try:
                    counsellor_fac_id = resolver.resolve_counsellor_faculty_id(principal)
                    is_mentee = resolver.is_student_assigned_mentee(counsellor_fac_id, str(target_student))
                except Exception:
                    is_mentee = False
                if not is_mentee:
                    logger.info(
                        f"Counsellor {principal.username} attempted student listing for target '{target_student}' outside mentorship: denied."
                    )
                    return AuthorizationDecision(
                        allowed=False,
                        reason_code="SCOPE_OUT_OF_BOUNDS",
                        message="You are not authorized to view student records outside your assigned mentee scope.",
                    )

            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                effective_scope={
                    "scope_type": ScopeType.SELF.value,
                    "scope_id": principal.person_id,
                },
                message="Counsellor mentee list access authorized.",
            )

        # 5. MENTOR Role: Bounded strictly to assigned mentees
        if principal.has_role("MENTOR") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC", "CAMPUS_ADMIN"):
            # Mentors can only query their own mentees; arbitrary cohort queries outside their mentees are prohibited
            if user_dept or filters.get("programme") or filters.get("batch"):
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    message="You are not authorized to view student records outside your assigned mentee scope.",
                )

            return AuthorizationDecision(
                allowed=True,
                reason_code="AUTHORIZED",
                effective_scope={
                    "scope_type": ScopeType.SELF.value,
                    "scope_id": principal.person_id or principal.user_id,
                },
                message="Mentor mentee access authorized.",
            )

        # 6. MANAGEMENT Role: Restricted from operational student-level personal record queries
        if principal.has_role("MANAGEMENT") and not principal.has_any_role(
            "PRINCIPAL", "DEAN", "IQAC", "CAMPUS_ADMIN"
        ):
            return AuthorizationDecision(
                allowed=False,
                reason_code="SCOPE_OUT_OF_BOUNDS",
                message="Management accounts are restricted to institutional analytics and cannot access operational student records.",
            )

        # 7. PRINCIPAL / DEAN / IQAC / CAMPUS_ADMIN: Institution-wide access
        return AuthorizationDecision(
            allowed=True,
            reason_code="AUTHORIZED",
            effective_scope={
                "scope_type": ScopeType.INSTITUTION.value,
                "scope_id": None,
            },
            message="Institutional student access authorized.",
        )


# Singleton instance
_authorization_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    global _authorization_service
    if _authorization_service is None:
        _authorization_service = AuthorizationService()
    return _authorization_service
