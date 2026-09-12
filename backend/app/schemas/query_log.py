"""Agent 63 - Phase 13: Query Logging Schemas
Defines the safe, privacy-bounded event schema for analytical query logging
and popular-question aggregation.

CRITICAL PRIVACY INVARIANTS:
- NO passwords, JWTs, API keys, connection strings, or bearer tokens.
- NO raw SQL statements.
- NO raw database result rows.
- NO email addresses or personal identifiers beyond internal user_id.
- NO full natural language query text (use bounded safe_query_label only if configured).
- NO conversation transcripts or prior turn content.
- NO confidential counselling data.
- user_id is the internal UUID only — never returned in popular-question output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class QueryLogEventType(str, Enum):
    """Distinguishes the source context of an analytical query event."""
    MANUAL_QUERY = "MANUAL_QUERY"
    FOLLOW_UP_QUERY = "FOLLOW_UP_QUERY"
    DRY_RUN = "DRY_RUN"
    DASHBOARD_REFRESH = "DASHBOARD_REFRESH"
    SCHEDULED_DASHBOARD_REFRESH = "SCHEDULED_DASHBOARD_REFRESH"
    EXPORT = "EXPORT"


class QueryLogStatus(str, Enum):
    """Safe high-level outcome status for a logged analytical event."""
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTENT_UNRESOLVED = "INTENT_UNRESOLVED"


class QueryLogEvent(BaseModel):
    """
    Bounded, privacy-safe record of a single analytical query execution event.

    Stores ONLY:
    - Internal trace identifiers (request_id, event_id)
    - Internal user_id UUID (never email, JWT, or credential)
    - Authorized semantic metric ID and query metadata
    - Execution outcome and performance metrics
    - Safe categorical metadata (visualization type, anomaly status)
    - Dashboard/widget identifiers if applicable

    Explicitly DOES NOT store:
    - Passwords, JWTs, API keys, connection strings
    - Raw SQL statements
    - Raw database result rows or row content
    - Email addresses or other personal details
    - Conversation history or prior turn content
    - Stack traces containing credentials or secrets
    - Confidential student or counselling data
    """
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this log event.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Trace correlation ID from the HTTP request.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description=(
            "Internal user UUID only. Never email, JWT, or credential. "
            "Never returned in popular-question API responses."
        ),
    )
    role: Optional[str] = Field(
        default=None,
        description="Primary role of the authenticated principal at execution time.",
    )
    scope_type: Optional[str] = Field(
        default=None,
        description="Scope type (INSTITUTION, DEPARTMENT, CAMPUS, COURSE_OFFERING, SELF).",
    )
    scope_id: Optional[str] = Field(
        default=None,
        description="Internal scope identifier (department ID, campus ID) for scope authorization. Never exposed in API responses.",
    )
    metric_id: Optional[str] = Field(
        default=None,
        description="Authoritative semantic metric ID (e.g. 'attendance.percentage').",
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Intent type from StructuredIntent (e.g. 'METRIC_QUERY').",
    )
    dimensions: List[str] = Field(
        default_factory=list,
        description="Ordered list of dimension key names queried (e.g. ['dim.department']).",
    )
    filter_keys: List[str] = Field(
        default_factory=list,
        description=(
            "Filter KEYS only — never filter values. "
            "Prevents leaking confidential filter values like student IDs."
        ),
    )
    event_type: QueryLogEventType = Field(
        default=QueryLogEventType.MANUAL_QUERY,
        description="Source context: manual, dashboard, scheduled, follow-up, or dry-run.",
    )
    status: QueryLogStatus = Field(
        ...,
        description="Safe high-level outcome of the query event.",
    )
    error_category: Optional[str] = Field(
        default=None,
        description=(
            "Safe generic error category if status != SUCCESS. "
            "Examples: AUTHORIZATION_DENIED, SQL_VALIDATION_FAILED, DB_UNAVAILABLE. "
            "Never contains raw exception details, stack traces, or secrets."
        ),
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Query execution duration in milliseconds.",
    )
    row_count: int = Field(
        default=0,
        ge=0,
        description="Number of result rows returned. Does NOT contain row content.",
    )
    visualization_type: Optional[str] = Field(
        default=None,
        description="Deterministic visualization type selected (KPI, BAR, LINE, TABLE, etc.).",
    )
    anomaly_status: Optional[str] = Field(
        default=None,
        description="Safe anomaly status label (NORMAL, ANOMALOUS, INSUFFICIENT_DATA).",
    )
    anomaly_method: Optional[str] = Field(
        default=None,
        description="Anomaly detection method applied (THRESHOLD, STATISTICAL, etc.).",
    )
    dashboard_id: Optional[str] = Field(
        default=None,
        description="Dashboard identifier if this event originated from a dashboard widget.",
    )
    widget_id: Optional[str] = Field(
        default=None,
        description="Widget identifier within a dashboard, if applicable.",
    )
    is_follow_up: bool = Field(
        default=False,
        description="True if this query inherited context from a prior conversation turn.",
    )
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event occurrence.",
    )
    safe_query_label: Optional[str] = Field(
        default=None,
        description=(
            "Optional bounded, sanitized analytical label derived from metric display name. "
            "Stored ONLY if QUERY_LOG_SAFE_QUERY_LABEL_MAX_LEN > 0 in configuration. "
            "Never contains raw SQL, credentials, or confidential content."
        ),
        max_length=500,
    )

    model_config = {"frozen": False}


class PopularQuestion(BaseModel):
    """
    Aggregated analytical pattern record for the popular-questions API response.

    PRIVACY GUARANTEE:
    - No user_id, username, email, or any user-identifying information.
    - No raw SQL.
    - No raw query text.
    - No raw result content.
    - Derived from metric_id and dimension signatures only.
    """
    metric_id: str = Field(
        ...,
        description="Authoritative semantic metric ID.",
    )
    label: str = Field(
        ...,
        description="Human-readable metric label from the semantic registry.",
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Most common intent type for this pattern.",
    )
    dimension_signature: str = Field(
        default="",
        description="Sorted, comma-separated dimension keys (e.g. 'dim.department,dim.term').",
    )
    count: int = Field(
        ...,
        ge=1,
        description="Number of times this analytical pattern was queried in the aggregation window.",
    )
    percentage: Optional[float] = Field(
        default=None,
        description="Share of this pattern as a percentage of all logged events in the window.",
    )
    last_seen: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the most recent logged event for this pattern.",
    )
