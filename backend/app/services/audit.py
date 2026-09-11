"""
Agent 63 – Audit Logging Abstraction
Models audit events corresponding to identity.audit_log.
Records structured authentication and authorization events without persisting secrets,
passwords, or sensitive institutional tokens into log streams.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from backend.app.core.logging import get_logger, request_id_ctx_var

logger = get_logger("agent63.services.audit")


class AuditAction(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    AUTHORIZATION_DENIAL = "AUTHORIZATION_DENIAL"
    PRIVILEGE_ESCALATION_ATTEMPT = "PRIVILEGE_ESCALATION_ATTEMPT"
    METRIC_ACCESS_DENIED = "METRIC_ACCESS_DENIED"


class AuthAuditEvent(BaseModel):
    """Structured security audit event record."""
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: AuditAction
    actor_user_id: Optional[str] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    request_id: Optional[str] = None
    source_ip: Optional[str] = None
    resource: Optional[str] = None
    reason: Optional[str] = None
    justification: Optional[str] = None


class AuditService:
    """Centralized security audit dispatcher."""

    def log_event(self, event: AuthAuditEvent) -> None:
        """Emits structured audit log record with correlation ID."""
        req_id = event.request_id or request_id_ctx_var.get()

        logger.info(
            f"SECURITY AUDIT: action={event.action.value} "
            f"actor={event.actor_username or event.actor_user_id or 'anonymous'} "
            f"role={event.actor_role or 'none'} "
            f"resource={event.resource or 'none'} "
            f"reason={event.reason or 'none'} "
            f"req_id={req_id}"
        )


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
