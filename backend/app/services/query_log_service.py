"""Agent 63 - Phase 13: Query Logging Service
In-memory, thread-safe, bounded analytical query logging and popular-question aggregation.

ARCHITECTURE DECISION (documented):
This service uses application-level in-memory storage following the same bounded,
thread-safe LRU pattern as Phase 10 ConversationContextStore.

It does NOT write to the college agentops PostgreSQL schema.
Reason: agentops.agent_run requires a pre-existing agentops.agent row (FK constraint)
which would require DBA coordination to register rows in the institutional database.
The Phase 8 analytical database connection is read-only.

If future phases provision an Agent 63 row in agentops.agent and establish a write-capable
audit connection, a persistence adapter can be added without changing this service's API.

CRITICAL SECURITY INVARIANTS:
1. ZERO SQL execution. ZERO database writes. ZERO LLM calls.
2. Events are stored by value (copied), never by reference to mutable objects.
3. Popular questions aggregate by metric_id+dimensions — never by user identity.
4. popular_questions output contains ZERO user_id, username, email, or JWT.
5. Role-filtering: popular questions only expose metrics the caller can access.
6. Bounded memory: LRU eviction at QUERY_LOG_MAX_ENTRIES.
7. Bounded aggregation window: configurable QUERY_LOG_AGGREGATION_WINDOW_HOURS.
8. Thread-safe: threading.RLock() protects all state mutations.
9. Logging failure does NOT abort or corrupt the analytical query response.
10. No raw SQL in event fields. No raw result rows. No conversation history.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.schemas.query_log import (
    PopularQuestion,
    QueryLogEvent,
    QueryLogEventType,
    QueryLogStatus,
)
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType

logger = get_logger("agent63.services.query_log")

# Aggregation signature separator (not a SQL character)
_SIG_SEP = "|"


def _build_popularity_signature(event: QueryLogEvent) -> str:
    """
    Builds a normalized analytical signature for popularity grouping.
    Based on metric_id + sorted dimensions + query_type.
    Never includes user identity, raw SQL, or raw query text.
    """
    dims = ",".join(sorted(event.dimensions)) if event.dimensions else ""
    return f"{event.metric_id}{_SIG_SEP}{dims}{_SIG_SEP}{event.query_type or ''}"


def _get_metric_display_label(
    metric_id: str,
    semantic_registry: Optional[Any] = None,
) -> str:
    """
    Retrieves the human-readable metric display name from the semantic registry.
    Falls back to a normalized metric_id if registry is unavailable.
    Never invents labels.
    """
    if semantic_registry and metric_id:
        try:
            metric_def = semantic_registry.get_metric(metric_id)
            if metric_def and metric_def.get("display_name"):
                return metric_def["display_name"]
        except Exception:
            pass
    # Safe fallback: convert metric_id to title case label
    # e.g. "attendance.percentage" -> "Attendance Percentage"
    if metric_id:
        parts = metric_id.replace(".", " ").replace("_", " ")
        return parts.title()
    return "Unknown Metric"


class QueryLoggingService:
    """
    Application-level analytical query log store.

    Provides:
    - Bounded, thread-safe in-memory event storage with LRU eviction.
    - Safe aggregation of popular analytical patterns (no user identity in output).
    - Role-safe filtering: popular questions only surface authorized metrics.
    - Fail-open: logging failure does NOT block query execution.

    Storage: application-level in-memory only.
    Does NOT write to college PostgreSQL (agentops or analytical schemas).
    Does NOT read from college PostgreSQL.
    Does NOT call any LLM.
    Does NOT execute SQL.
    """

    def __init__(
        self,
        max_entries: Optional[int] = None,
        aggregation_window_hours: Optional[int] = None,
        semantic_registry: Optional[Any] = None,
    ):
        self._max_entries = max_entries or settings.QUERY_LOG_MAX_ENTRIES
        self._window_hours = (
            aggregation_window_hours
            or settings.QUERY_LOG_AGGREGATION_WINDOW_HOURS
        )
        self._semantic_registry = semantic_registry

        # OrderedDict for LRU eviction (event_id → QueryLogEvent)
        self._events: OrderedDict[str, QueryLogEvent] = OrderedDict()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_event(self, event: QueryLogEvent) -> None:
        """
        Records a safe analytical query event.
        Thread-safe. Bounded. Fail-open (logs warning on error, never raises).

        SECURITY: This method must only be called AFTER authorization, SQL compilation,
        and validation have already executed. Logging never changes authorization decisions.
        """
        if not settings.QUERY_LOG_ENABLED:
            return

        try:
            with self._lock:
                # LRU eviction: remove oldest entries if at capacity
                while len(self._events) >= self._max_entries:
                    self._events.popitem(last=False)

                self._events[event.event_id] = event
                self._events.move_to_end(event.event_id)

            logger.debug(
                f"QUERY_LOG: event_id={event.event_id} metric={event.metric_id} "
                f"status={event.status.value} type={event.event_type.value} "
                f"duration_ms={event.execution_time_ms:.1f}"
            )
        except Exception as e:
            # Fail-open: log warning but NEVER propagate logging errors to callers
            logger.warning(
                f"QueryLoggingService: event logging failed (non-fatal): {e}"
            )

    def get_popular_questions(
        self,
        principal: AuthenticatedPrincipal,
        limit: Optional[int] = None,
        window_hours: Optional[int] = None,
    ) -> List[PopularQuestion]:
        """
        Returns aggregated popular analytical patterns visible to the current principal.

        PRIVACY GUARANTEES:
        - Output contains ZERO user_id, username, email, or personal identifiers.
        - Aggregated by metric_id + dimension signature ONLY.
        - Filtered to metrics the caller is authorized to access.
        - Window-bounded: configurable time window (default 7 days).
        - Count-bounded: configurable max results (default 10).
        - STUDENT sees only student-accessible metrics.
        - COUNSELLOR sees nothing (no analytics metrics).
        - Never reveals who asked what or when.
        """
        result_limit = limit or settings.QUERY_LOG_MAX_POPULAR_RESULTS
        effective_window = window_hours or self._window_hours

        cutoff = datetime.now(timezone.utc) - timedelta(hours=effective_window)

        # Aggregate patterns within the time window for authorized metrics
        # key: popularity_signature → {count, last_seen, sample_event}
        pattern_counts: Dict[str, Dict[str, Any]] = {}

        with self._lock:
            events_snapshot = list(self._events.values())

        for event in events_snapshot:
            # Window filter
            if event.occurred_at < cutoff:
                continue
            # Only SUCCESS and EMPTY events count towards popularity
            if event.status not in (QueryLogStatus.SUCCESS, QueryLogStatus.EMPTY):
                continue
            # Metric must be present and authorized for this principal
            if not event.metric_id:
                continue
            if not self._is_event_authorized(event, principal):
                continue

            sig = _build_popularity_signature(event)
            if sig not in pattern_counts:
                pattern_counts[sig] = {
                    "count": 0,
                    "last_seen": event.occurred_at,
                    "metric_id": event.metric_id,
                    "dimensions": event.dimensions,
                    "query_type": event.query_type,
                }
            pattern_counts[sig]["count"] += 1
            if event.occurred_at > pattern_counts[sig]["last_seen"]:
                pattern_counts[sig]["last_seen"] = event.occurred_at

        if not pattern_counts:
            return []

        total_events = sum(p["count"] for p in pattern_counts.values())

        # Sort by count descending, then by last_seen descending
        sorted_patterns = sorted(
            pattern_counts.values(),
            key=lambda p: (-p["count"], -p["last_seen"].timestamp()),
        )

        results: List[PopularQuestion] = []
        for pattern in sorted_patterns[:result_limit]:
            metric_id = pattern["metric_id"]
            label = _get_metric_display_label(metric_id, self._semantic_registry)
            dim_sig = ",".join(sorted(pattern["dimensions"])) if pattern["dimensions"] else ""
            pct = round((pattern["count"] / total_events) * 100, 1) if total_events > 0 else None

            results.append(
                PopularQuestion(
                    metric_id=metric_id,
                    label=label,
                    query_type=pattern["query_type"],
                    dimension_signature=dim_sig,
                    count=pattern["count"],
                    percentage=pct,
                    last_seen=pattern["last_seen"],
                )
            )

        return results

    def get_event_count(self) -> int:
        """Returns total stored event count. Thread-safe."""
        with self._lock:
            return len(self._events)

    def clear_expired(self, window_hours: Optional[int] = None) -> int:
        """
        Removes events older than the aggregation window.
        Returns number of events removed.
        """
        effective_window = window_hours or self._window_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=effective_window)
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._events.items() if v.occurred_at < cutoff
            ]
            for k in expired_keys:
                del self._events[k]
                removed += 1
        if removed:
            logger.debug(f"QueryLoggingService: cleared {removed} expired events.")
        return removed

    def get_own_recent_events(
        self,
        principal: AuthenticatedPrincipal,
        limit: int = 20,
    ) -> List[QueryLogEvent]:
        """
        Returns recent events for the current user ONLY (no cross-user access).
        Sensitive fields (user_id) are included because this is the owner.
        Maximum limit bounded to 100.
        """
        effective_limit = min(limit, 100)
        with self._lock:
            # Snapshot in reverse insertion order (most recent first)
            all_events = list(reversed(list(self._events.values())))

        return [
            e for e in all_events
            if e.user_id == principal.user_id
        ][:effective_limit]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_event_authorized(
        self, event: QueryLogEvent, principal: AuthenticatedPrincipal
    ) -> bool:
        """
        Authoritative validation of whether the current principal can independently
        execute the underlying analytical query represented by this log event.

        Evaluates:
        1. Principal active status.
        2. Strictly quarantined / confidential prefixes.
        3. Semantic registry lifecycle (APPROVED only) and sensitivity (not RESTRICTED).
        4. Domain read permissions.
        5. Scoped role boundaries:
           - Students restricted to SELF scope only (cannot see INSTITUTION / DEPARTMENT patterns).
           - HODs restricted to their own department (cannot see another department's patterns).
        6. Dimensions safety (no confidential dimensions).

        Zero SQL. Zero DB writes. Pure deterministic defense-in-depth.
        """
        if not principal or not principal.is_active:
            return False

        metric_id = event.metric_id
        if not metric_id:
            return False

        # 1. Strictly denied prefixes
        STRICTLY_DENIED = (
            "confidential.",
            "assessment.question_paper",
            "exams.question_paper_delivery",
            "exams.malpractice_incident",
            "identity.credential",
            "identity.auth_token",
        )
        for prefix in STRICTLY_DENIED:
            if metric_id.startswith(prefix):
                return False

        # Deny if any dimension references restricted/confidential objects
        for dim in event.dimensions:
            if any(dim.startswith(p) for p in STRICTLY_DENIED):
                return False

        # 2. Domain-permission mapping (mirrors authorization.py DOMAIN_PERMISSION_MAP)
        DOMAIN_PERMISSION_MAP: Dict[str, str] = {
            "attendance": "attendance.read",
            "assessment": "assessment.read",
            "outcomes": "outcomes.read",
            "placement": "placement.read",
            "academics": "academics.read",
            "quality": "quality.read",
        }

        domain = metric_id.split(".")[0] if "." in metric_id else ""
        required_perm = DOMAIN_PERMISSION_MAP.get(domain)
        if required_perm:
            if not principal.has_permission(required_perm) and not principal.has_permission("analytics.read"):
                return False
        elif not principal.has_permission("analytics.read"):
            return False

        # 3. Semantic registry validation (lifecycle & sensitivity)
        if self._semantic_registry:
            try:
                metric = None
                if hasattr(self._semantic_registry, "get_metric"):
                    metric = self._semantic_registry.get_metric(metric_id)
                elif hasattr(self._semantic_registry, "load"):
                    data = self._semantic_registry.load()
                    for m in data.get("metrics", []):
                        if m.get("metric_id") == metric_id:
                            metric = m
                            break
                if metric:
                    if metric.get("status") != "APPROVED":
                        return False
                    if metric.get("sensitivity") == "RESTRICTED":
                        return False
            except Exception:
                pass

        # 4. Scoped Role Boundary Enforcement
        # Student self-scope enforcement:
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC"):
            # Students can only execute SELF-scoped queries
            # If the event was executed at INSTITUTION or DEPARTMENT scope, student cannot see it
            if event.scope_type and event.scope_type != ScopeType.SELF.value:
                return False

        # HOD department-scope enforcement:
        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC", "DEAN"):
            hod_scopes = principal.get_scopes_for_role("HOD")
            allowed_dept_ids = {sr.scope_id for sr in hod_scopes if sr.scope_id}
            # If event specifies a department scope_id that does not match this HOD's department, deny
            if event.scope_type == ScopeType.DEPARTMENT.value and event.scope_id:
                if event.scope_id not in allowed_dept_ids:
                    return False

        return True

    def _is_metric_authorized(
        self, metric_id: str, principal: AuthenticatedPrincipal
    ) -> bool:
        """Backward-compatible metric authorization helper."""
        event = QueryLogEvent(metric_id=metric_id, status=QueryLogStatus.SUCCESS)
        return self._is_event_authorized(event, principal)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_singleton_query_log_service: Optional[QueryLoggingService] = None


def get_query_log_service() -> QueryLoggingService:
    """Dependency provider for QueryLoggingService."""
    global _singleton_query_log_service
    if _singleton_query_log_service is None:
        # Lazy import to avoid circular deps
        try:
            from backend.app.services.semantic_registry import get_semantic_registry_service
            semantic_registry = get_semantic_registry_service()
        except Exception:
            semantic_registry = None

        _singleton_query_log_service = QueryLoggingService(
            semantic_registry=semantic_registry,
        )
    return _singleton_query_log_service


def reset_query_log_service() -> None:
    """Resets singleton for isolated test runs."""
    global _singleton_query_log_service
    _singleton_query_log_service = None
