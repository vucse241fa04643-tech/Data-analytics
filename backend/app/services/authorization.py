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
            if requested_scope_type and requested_scope_type != ScopeType.SELF:
                return AuthorizationDecision(
                    allowed=False,
                    reason_code="SCOPE_OUT_OF_BOUNDS",
                    metric_id=metric_id,
                    message="Student accounts are restricted to self-scoped records.",
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


# Singleton instance
_authorization_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    global _authorization_service
    if _authorization_service is None:
        _authorization_service = AuthorizationService()
    return _authorization_service
