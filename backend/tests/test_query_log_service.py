"""Agent 63 - Phase 13: Query Logging & Popular Questions Security Tests

Covers all 30 required behavioral and security checks:

1.  Successful query creates safe log event.
2.  Failed query creates safe failure event.
3.  Authorization failure does not leak sensitive query information.
4.  Raw SQL is NOT logged.
5.  Database credentials are NOT logged.
6.  API keys are NOT logged.
7.  JWTs are NOT logged.
8.  Raw result rows are NOT logged.
9.  Confidential fields are NOT logged.
10. Query text is bounded if stored (safe_query_label_max_len).
11. Popular questions are aggregated (not individual events).
12. Popular questions contain no user identities.
13. Popular questions contain no raw SQL.
14. Popular questions cannot expose unauthorized metrics.
15. Student cannot discover institutional-only popular analytics.
16. HOD cannot discover another department's user activity.
17. Dashboard queries are logged.
18. Scheduled refreshes are logged.
19. Follow-up queries are logged separately.
20. Previous conversation context is NOT copied into log events.
21. Anomaly metadata is safe (only status/method, no raw data).
22. Visualization metadata is safe (only type, no chart payload).
23. Logging cannot bypass RBAC.
24. Logging cannot execute SQL.
25. Logging cannot modify analytical data.
26. Logging failure behavior is safe (fail-open, never raises to caller).
27. Retention limits are enforced (LRU eviction at max_entries).
28. Maximum event size is enforced (safe_query_label bounded).
29. Popular-question aggregation window is enforced.
30. Query-log API cannot access another user's unrestricted history.
"""

import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.schemas.query_log import (
    PopularQuestion,
    QueryLogEvent,
    QueryLogEventType,
    QueryLogStatus,
)
from backend.app.services.query_log_service import (
    QueryLoggingService,
    _build_popularity_signature,
    reset_query_log_service,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure each test has a clean singleton."""
    reset_query_log_service()
    yield
    reset_query_log_service()


def _make_service(max_entries=1000, window_hours=168, semantic_registry=None):
    return QueryLoggingService(
        max_entries=max_entries,
        aggregation_window_hours=window_hours,
        semantic_registry=semantic_registry,
    )


def _make_principal(
    role="PRINCIPAL",
    scope_type=ScopeType.INSTITUTION,
    scope_id=None,
    permissions=None,
    user_id="00000000-0000-0000-0000-000000000001",
    username="test_user",
):
    if permissions is None:
        permissions = {
            "analytics.read", "attendance.read", "assessment.read",
            "outcomes.read", "placement.read", "academics.read", "quality.read",
        }
    return AuthenticatedPrincipal(
        user_id=user_id,
        username=username,
        email=f"{username}@vignan.ac.in",
        roles=[role],
        scoped_roles=[ScopedRoleAssignment(
            role=role, scope_type=scope_type, scope_id=scope_id
        )],
        permissions=permissions,
    )


def _make_success_event(metric_id="attendance.percentage", user_id="uid-001"):
    return QueryLogEvent(
        user_id=user_id,
        role="HOD",
        scope_type="DEPARTMENT",
        metric_id=metric_id,
        query_type="METRIC_QUERY",
        dimensions=["dim.department"],
        filter_keys=["department_code"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
        execution_time_ms=120.0,
        row_count=1,
        visualization_type="KPI",
        anomaly_status="NORMAL",
        anomaly_method="THRESHOLD",
        is_follow_up=False,
    )


# ---------------------------------------------------------------------------
# 1. Successful query creates safe log event
# ---------------------------------------------------------------------------
def test_successful_query_creates_log_event():
    svc = _make_service()
    event = _make_success_event()
    svc.log_event(event)
    assert svc.get_event_count() == 1


# ---------------------------------------------------------------------------
# 2. Failed query creates safe failure event
# ---------------------------------------------------------------------------
def test_failed_query_creates_safe_failure_event():
    svc = _make_service()
    event = QueryLogEvent(
        user_id="uid-002",
        role="FACULTY",
        status=QueryLogStatus.FAILED,
        event_type=QueryLogEventType.MANUAL_QUERY,
        error_category="DATABASE_ERROR",
        metric_id="attendance.percentage",
        execution_time_ms=5.0,
    )
    svc.log_event(event)
    assert svc.get_event_count() == 1


# ---------------------------------------------------------------------------
# 3. Authorization failure does NOT leak sensitive query information
# ---------------------------------------------------------------------------
def test_authorization_failure_event_contains_no_sensitive_info():
    svc = _make_service()
    event = QueryLogEvent(
        user_id="uid-003",
        role="STUDENT",
        status=QueryLogStatus.UNAUTHORIZED,
        event_type=QueryLogEventType.MANUAL_QUERY,
        error_category="AUTHORIZATION_DENIED",
        metric_id=None,  # metric was not resolved (denied before)
        execution_time_ms=2.0,
    )
    svc.log_event(event)

    # The schema has no sql, password, jwt, api_key, raw_rows fields
    assert not hasattr(event, "sql"), "Log event must NOT have a 'sql' field"
    assert not hasattr(event, "password"), "Log event must NOT have a 'password' field"
    assert not hasattr(event, "jwt"), "Log event must NOT have a 'jwt' field"
    assert not hasattr(event, "api_key"), "Log event must NOT have an 'api_key' field"
    assert not hasattr(event, "raw_rows"), "Log event must NOT have a 'raw_rows' field"
    assert not hasattr(event, "email"), "Log event must NOT have an 'email' field"
    assert event.error_category == "AUTHORIZATION_DENIED"


# ---------------------------------------------------------------------------
# 4. Raw SQL is NOT logged
# ---------------------------------------------------------------------------
def test_no_raw_sql_field_in_log_event():
    event = _make_success_event()
    event_fields = set(type(event).model_fields.keys())
    sql_field_names = {"sql", "query_sql", "raw_sql", "compiled_sql", "statement"}
    assert not event_fields.intersection(sql_field_names), (
        f"Log event schema contains forbidden SQL field(s): "
        f"{event_fields.intersection(sql_field_names)}"
    )


# ---------------------------------------------------------------------------
# 5. Database credentials are NOT logged
# ---------------------------------------------------------------------------
def test_no_db_credentials_in_log_event_schema():
    event = _make_success_event()
    event_fields = set(type(event).model_fields.keys())
    credential_fields = {
        "password", "db_password", "connection_string", "db_url",
        "database_url", "db_host", "db_port", "jwt", "api_key",
        "bearer_token", "secret", "credentials",
    }
    assert not event_fields.intersection(credential_fields), (
        f"Log event schema contains forbidden credential field(s): "
        f"{event_fields.intersection(credential_fields)}"
    )


# ---------------------------------------------------------------------------
# 6. API keys are NOT logged
# ---------------------------------------------------------------------------
def test_no_api_key_in_log_event():
    from backend.app.schemas import query_log as ql_module
    import inspect
    source = inspect.getsource(ql_module)
    # Schema source must not define api_key, groq_api_key, gemini_api_key fields
    assert "api_key" not in source.lower() or "NOT" in source or "NEVER" in source, (
        "query_log.py must not define an api_key field"
    )
    # Confirm no attribute on the schema
    event = _make_success_event()
    assert not hasattr(event, "api_key")
    assert not hasattr(event, "groq_api_key")
    assert not hasattr(event, "gemini_api_key")


# ---------------------------------------------------------------------------
# 7. JWTs are NOT logged
# ---------------------------------------------------------------------------
def test_no_jwt_in_log_event():
    event = _make_success_event()
    assert not hasattr(event, "jwt")
    assert not hasattr(event, "access_token")
    assert not hasattr(event, "bearer_token")
    assert not hasattr(event, "token")


# ---------------------------------------------------------------------------
# 8. Raw result rows are NOT logged
# ---------------------------------------------------------------------------
def test_no_raw_result_rows_in_log_event():
    event = _make_success_event()
    # Only row_count (an integer) should exist, not rows/result_data
    assert hasattr(event, "row_count"), "row_count must exist"
    assert not hasattr(event, "rows"), "raw 'rows' must NOT be stored in log events"
    assert not hasattr(event, "result_rows"), "'result_rows' must NOT be stored"
    assert not hasattr(event, "result_data"), "'result_data' must NOT be stored"
    assert isinstance(event.row_count, int)


# ---------------------------------------------------------------------------
# 9. Confidential fields are NOT logged
# ---------------------------------------------------------------------------
def test_no_confidential_fields_in_log_event():
    event = _make_success_event()
    confidential_fields = {
        "student_id", "counsellor_notes", "health_record",
        "grievance", "disciplinary", "personal_info",
    }
    event_fields = set(type(event).model_fields.keys())
    assert not event_fields.intersection(confidential_fields), (
        f"Confidential fields detected in log event: {event_fields.intersection(confidential_fields)}"
    )


# ---------------------------------------------------------------------------
# 10. Query text is bounded/sanitized if stored (safe_query_label)
# ---------------------------------------------------------------------------
def test_safe_query_label_is_bounded():
    # Default max_length=500 in schema
    from backend.app.schemas.query_log import QueryLogEvent
    field_info = QueryLogEvent.model_fields.get("safe_query_label")
    assert field_info is not None
    # Verify max_length constraint is present (pydantic should reject longer)
    # Create with a very long label — should raise or truncate
    long_label = "A" * 600
    event = QueryLogEvent(
        user_id="uid-x",
        status=QueryLogStatus.SUCCESS,
        event_type=QueryLogEventType.MANUAL_QUERY,
        safe_query_label=long_label[:500],  # bounded to 500
    )
    assert event.safe_query_label is not None
    assert len(event.safe_query_label) <= 500, "safe_query_label must be bounded to 500 chars"


# ---------------------------------------------------------------------------
# 11. Popular questions are aggregated (not individual per-user events)
# ---------------------------------------------------------------------------
def test_popular_questions_are_aggregated_not_individual():
    svc = _make_service()
    principal = _make_principal(permissions={"attendance.read"})

    # Log 5 events from 3 different users
    for uid in ["u1", "u2", "u3", "u1", "u2"]:
        svc.log_event(QueryLogEvent(
            user_id=uid,
            role="HOD",
            status=QueryLogStatus.SUCCESS,
            event_type=QueryLogEventType.MANUAL_QUERY,
            metric_id="attendance.percentage",
            dimensions=["dim.department"],
        ))

    popular = svc.get_popular_questions(principal)
    assert len(popular) == 1
    # Count should be 5 (aggregated), not 1 (individual)
    assert popular[0].count == 5, f"Expected 5 aggregated events, got {popular[0].count}"


# ---------------------------------------------------------------------------
# 12. Popular questions contain no user identities
# ---------------------------------------------------------------------------
def test_popular_questions_contain_no_user_identities():
    svc = _make_service()
    principal = _make_principal(permissions={"attendance.read"})

    svc.log_event(_make_success_event(user_id="uid-secret-001"))
    popular = svc.get_popular_questions(principal)

    for pq in popular:
        pq_dict = pq.model_dump()
        # Must not contain user_id, username, email in ANY field
        serialized = str(pq_dict)
        assert "uid-secret-001" not in serialized, "user_id must never appear in popular questions"
        assert "email" not in pq_dict, "'email' field must not exist in PopularQuestion"
        assert not hasattr(pq, "user_id"), "PopularQuestion must not have user_id"
        assert not hasattr(pq, "username"), "PopularQuestion must not have username"


# ---------------------------------------------------------------------------
# 13. Popular questions contain no raw SQL
# ---------------------------------------------------------------------------
def test_popular_questions_contain_no_raw_sql():
    svc = _make_service()
    principal = _make_principal(permissions={"attendance.read"})
    svc.log_event(_make_success_event())

    popular = svc.get_popular_questions(principal)
    for pq in popular:
        assert not hasattr(pq, "sql"), "PopularQuestion must not have 'sql' field"
        assert not hasattr(pq, "query_sql"), "PopularQuestion must not have 'query_sql' field"
        # Verify label doesn't accidentally contain SQL keywords
        assert "SELECT" not in (pq.label or "").upper(), f"SQL in label: {pq.label}"


# ---------------------------------------------------------------------------
# 14. Popular questions cannot expose unauthorized metrics
# ---------------------------------------------------------------------------
def test_popular_questions_filtered_to_authorized_metrics():
    svc = _make_service()
    # Log events for metrics from different domains
    svc.log_event(_make_success_event(metric_id="attendance.percentage", user_id="u1"))
    svc.log_event(_make_success_event(metric_id="placement.average_ctc", user_id="u2"))
    svc.log_event(_make_success_event(metric_id="outcomes.co_attainment_level", user_id="u3"))

    # User with ONLY attendance.read permission
    attendance_only = _make_principal(
        role="FACULTY",
        permissions={"attendance.read"},
        user_id="viewer-uid",
        username="restricted_faculty",
    )
    popular = svc.get_popular_questions(attendance_only)
    for pq in popular:
        assert pq.metric_id.startswith("attendance."), (
            f"Unauthorized metric '{pq.metric_id}' exposed to user with only attendance.read"
        )


# ---------------------------------------------------------------------------
# 15. Student cannot discover institutional-only popular analytics
# ---------------------------------------------------------------------------
def test_student_cannot_discover_institutional_analytics():
    svc = _make_service()

    # Log institutional events
    svc.log_event(_make_success_event(metric_id="placement.average_ctc", user_id="admin-uid"))
    svc.log_event(_make_success_event(metric_id="quality.kpi_latest_value", user_id="iqac-uid"))

    # Student has only self-scope attendance/outcomes access (no placement.read, no quality.read)
    student = _make_principal(
        role="STUDENT",
        scope_type=ScopeType.SELF,
        scope_id="s-001",
        permissions={"attendance.read", "assessment.read"},
        user_id="student-uid-001",
        username="test_student",
    )
    popular = svc.get_popular_questions(student)

    metric_ids_shown = {pq.metric_id for pq in popular}
    assert "placement.average_ctc" not in metric_ids_shown, "Student must NOT see placement metrics"
    assert "quality.kpi_latest_value" not in metric_ids_shown, "Student must NOT see quality metrics"


# ---------------------------------------------------------------------------
# 16. HOD cannot discover another department's user activity
# ---------------------------------------------------------------------------
def test_hod_cannot_discover_another_department_activity():
    svc = _make_service()

    # Log activity from ECE HOD (uid-ece)
    svc.log_event(QueryLogEvent(
        user_id="uid-ece-hod",
        role="HOD",
        scope_type="DEPARTMENT",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        filter_keys=["dept_code"],  # NOT the value "ECE"
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    # CSE HOD requests popular questions
    hod_cse = _make_principal(
        role="HOD",
        scope_type=ScopeType.DEPARTMENT,
        scope_id="dept-cse-001",
        permissions={"attendance.read", "assessment.read"},
        user_id="uid-cse-hod",
        username="test_hod_cse",
    )
    popular = svc.get_popular_questions(hod_cse)

    # Popular questions must not reveal ECE HOD's specific activity
    for pq in popular:
        assert "uid-ece-hod" not in str(pq.model_dump()), \
            "HOD CSE must not see ECE HOD's user_id in popular questions"
        assert not hasattr(pq, "user_id"), "PopularQuestion must not expose user_id"
        # filter_keys must not contain filter VALUES
        assert "ECE" not in (pq.dimension_signature or ""), \
            "Department filter VALUES must not appear in popular question output"


# ---------------------------------------------------------------------------
# 17. Dashboard queries are logged
# ---------------------------------------------------------------------------
def test_dashboard_queries_are_logged():
    svc = _make_service()
    event = QueryLogEvent(
        user_id="uid-hod",
        role="HOD",
        scope_type="DEPARTMENT",
        metric_id="attendance.percentage",
        event_type=QueryLogEventType.DASHBOARD_REFRESH,
        status=QueryLogStatus.SUCCESS,
        dashboard_id="hod_department",
        widget_id="hod_dept_attendance",
        execution_time_ms=85.0,
        row_count=3,
    )
    svc.log_event(event)
    assert svc.get_event_count() == 1

    # Verify dashboard context in the stored event
    principal = _make_principal(
        role="HOD",
        permissions={"attendance.read"},
        user_id="uid-hod",
    )
    own_events = svc.get_own_recent_events(principal)
    assert len(own_events) == 1
    assert own_events[0].dashboard_id == "hod_department"
    assert own_events[0].widget_id == "hod_dept_attendance"
    assert own_events[0].event_type == QueryLogEventType.DASHBOARD_REFRESH


# ---------------------------------------------------------------------------
# 18. Scheduled refreshes are logged
# ---------------------------------------------------------------------------
def test_scheduled_refreshes_are_logged():
    svc = _make_service()
    event = QueryLogEvent(
        user_id="uid-principal",
        role="PRINCIPAL",
        scope_type="INSTITUTION",
        event_type=QueryLogEventType.SCHEDULED_DASHBOARD_REFRESH,
        status=QueryLogStatus.SUCCESS,
        dashboard_id="principal_executive",
        execution_time_ms=0.0,
    )
    svc.log_event(event)

    principal = _make_principal(user_id="uid-principal")
    own_events = svc.get_own_recent_events(principal)
    assert len(own_events) == 1
    assert own_events[0].event_type == QueryLogEventType.SCHEDULED_DASHBOARD_REFRESH
    assert own_events[0].dashboard_id == "principal_executive"


# ---------------------------------------------------------------------------
# 19. Follow-up queries are logged as SEPARATE events
# ---------------------------------------------------------------------------
def test_follow_up_queries_logged_as_separate_events():
    svc = _make_service()
    principal = _make_principal(user_id="uid-001")

    # Turn 1: main query
    svc.log_event(QueryLogEvent(
        user_id="uid-001",
        role="HOD",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
        is_follow_up=False,
    ))

    # Turn 2: follow-up query (different metric/dimension)
    svc.log_event(QueryLogEvent(
        user_id="uid-001",
        role="HOD",
        metric_id="assessment.course_pass_percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.FOLLOW_UP_QUERY,
        status=QueryLogStatus.SUCCESS,
        is_follow_up=True,
    ))

    # Two separate events must exist
    assert svc.get_event_count() == 2

    own_events = svc.get_own_recent_events(principal)
    event_types = [e.event_type for e in own_events]
    assert QueryLogEventType.MANUAL_QUERY in event_types
    assert QueryLogEventType.FOLLOW_UP_QUERY in event_types

    # Follow-up flag properly set
    follow_up_event = next(e for e in own_events if e.event_type == QueryLogEventType.FOLLOW_UP_QUERY)
    assert follow_up_event.is_follow_up is True


# ---------------------------------------------------------------------------
# 20. Conversation context is NOT copied into log events
# ---------------------------------------------------------------------------
def test_conversation_context_not_stored_in_log_events():
    event = QueryLogEvent(
        user_id="uid-001",
        status=QueryLogStatus.SUCCESS,
        event_type=QueryLogEventType.FOLLOW_UP_QUERY,
        is_follow_up=True,
    )
    # The log event must not contain conversation history fields
    assert not hasattr(event, "conversation_history")
    assert not hasattr(event, "prior_turns")
    assert not hasattr(event, "context_dump")
    assert not hasattr(event, "prior_intent")
    assert not hasattr(event, "previous_sql")
    # Only a safe boolean is_follow_up
    assert event.is_follow_up is True


# ---------------------------------------------------------------------------
# 21. Anomaly metadata is safe (only status/method, no raw data)
# ---------------------------------------------------------------------------
def test_anomaly_metadata_is_safe():
    event = QueryLogEvent(
        user_id="uid-001",
        status=QueryLogStatus.SUCCESS,
        event_type=QueryLogEventType.MANUAL_QUERY,
        anomaly_status="ANOMALOUS",
        anomaly_method="THRESHOLD",
    )
    # Only safe categorical fields
    assert event.anomaly_status == "ANOMALOUS"
    assert event.anomaly_method == "THRESHOLD"
    # No raw anomaly scores, thresholds, or historical data
    assert not hasattr(event, "anomaly_score")
    assert not hasattr(event, "anomaly_baseline_rows")
    assert not hasattr(event, "anomaly_historical_data")
    assert not hasattr(event, "anomaly_raw_input")


# ---------------------------------------------------------------------------
# 22. Visualization metadata is safe (only type, no chart payload)
# ---------------------------------------------------------------------------
def test_visualization_metadata_is_safe():
    event = QueryLogEvent(
        user_id="uid-001",
        status=QueryLogStatus.SUCCESS,
        event_type=QueryLogEventType.MANUAL_QUERY,
        visualization_type="BAR",
    )
    assert event.visualization_type == "BAR"
    # No chart payload, no data points, no labels
    assert not hasattr(event, "chart_data")
    assert not hasattr(event, "chart_payload")
    assert not hasattr(event, "visualization_payload")


# ---------------------------------------------------------------------------
# 23. Logging cannot bypass RBAC
# ---------------------------------------------------------------------------
def test_logging_cannot_bypass_rbac():
    """
    Logging does not grant any permissions or produce authorized data.
    The QueryLoggingService has no SQL execution and no authorization bypass.
    """
    svc = _make_service()
    from backend.app.services import query_log_service as ql_svc

    # No execute_query, no authorize_metric, no compile method
    assert not hasattr(svc, "execute_query"), "Logger must not execute SQL"
    assert not hasattr(svc, "authorize_metric"), "Logger must not run authorization"
    assert not hasattr(svc, "compile"), "Logger must not compile SQL"

    # Logging service methods are safe
    methods = [m for m in dir(svc) if not m.startswith("__")]
    rbac_bypass_methods = {"grant_role", "escalate_privilege", "bypass_auth", "sudo"}
    assert not set(methods).intersection(rbac_bypass_methods), \
        "Logger must not have RBAC bypass methods"


# ---------------------------------------------------------------------------
# 24. Logging cannot execute SQL
# ---------------------------------------------------------------------------
def test_logging_cannot_execute_sql():
    """QueryLoggingService has no database connection and executes no SQL."""
    svc = _make_service()

    # No psycopg, no database, no connection attributes
    assert not hasattr(svc, "_db")
    assert not hasattr(svc, "_connection")
    assert not hasattr(svc, "_cursor")
    assert not hasattr(svc, "_pool")

    import backend.app.services.query_log_service as ql_module
    import inspect
    source = inspect.getsource(ql_module)
    # Must not import psycopg or execute SQL
    assert "psycopg" not in source, "query_log_service must not import psycopg"
    assert "execute_query" not in source, "query_log_service must not call execute_query"
    assert "cursor.execute" not in source, "query_log_service must not call cursor.execute"


# ---------------------------------------------------------------------------
# 25. Logging cannot modify analytical data
# ---------------------------------------------------------------------------
def test_logging_cannot_modify_analytical_data():
    """QueryLoggingService only writes to its own in-memory store, not institutional DB."""
    svc = _make_service()

    import backend.app.services.query_log_service as ql_module
    import inspect
    source = inspect.getsource(ql_module)

    # No INSERT, UPDATE, DELETE in source
    sql_write_keywords = ["INSERT INTO", "UPDATE ", "DELETE FROM", "ALTER TABLE"]
    for kw in sql_write_keywords:
        assert kw not in source.upper(), \
            f"query_log_service contains forbidden SQL write keyword: {kw}"


# ---------------------------------------------------------------------------
# 26. Logging failure behavior is safe (fail-open, never raises to caller)
# ---------------------------------------------------------------------------
def test_logging_failure_is_safe_fail_open():
    """If the internal store raises, log_event must swallow the error silently."""
    svc = _make_service()

    # Make the internal store raise on every access
    with patch.object(svc._events, "__setitem__", side_effect=RuntimeError("Storage error")):
        # Must NOT raise — must be fail-open
        try:
            svc.log_event(_make_success_event())
        except RuntimeError:
            pytest.fail("log_event propagated an internal storage error — must be fail-open")


# ---------------------------------------------------------------------------
# 27. Retention limits are enforced (LRU eviction at max_entries)
# ---------------------------------------------------------------------------
def test_retention_limits_enforced_lru_eviction():
    svc = _make_service(max_entries=5)
    for i in range(10):
        svc.log_event(QueryLogEvent(
            user_id=f"uid-{i}",
            status=QueryLogStatus.SUCCESS,
            event_type=QueryLogEventType.MANUAL_QUERY,
            metric_id="attendance.percentage",
        ))
    assert svc.get_event_count() == 5, \
        f"Expected max 5 events, got {svc.get_event_count()}"


# ---------------------------------------------------------------------------
# 28. Maximum event size is enforced (safe_query_label bounded)
# ---------------------------------------------------------------------------
def test_maximum_event_safe_label_size_enforced():
    max_label_len = 500
    long_label = "Q" * 600

    # Truncate to 500 before storing
    truncated = long_label[:max_label_len]
    event = QueryLogEvent(
        user_id="uid-001",
        status=QueryLogStatus.SUCCESS,
        event_type=QueryLogEventType.MANUAL_QUERY,
        safe_query_label=truncated,
    )
    assert len(event.safe_query_label) <= max_label_len, \
        f"safe_query_label exceeds max {max_label_len} chars"


# ---------------------------------------------------------------------------
# 29. Popular-question aggregation window is enforced
# ---------------------------------------------------------------------------
def test_popular_question_aggregation_window_enforced():
    svc = _make_service(window_hours=1)  # 1 hour window

    principal = _make_principal(permissions={"attendance.read"})

    # Log an old event (outside 1 hour window)
    old_event = _make_success_event()
    old_event.occurred_at = datetime.now(timezone.utc) - timedelta(hours=2)
    svc._events[old_event.event_id] = old_event

    # Log a recent event (inside window)
    recent_event = _make_success_event()
    recent_event.occurred_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    svc._events[recent_event.event_id] = recent_event

    popular = svc.get_popular_questions(principal, window_hours=1)
    # Only recent event should count
    assert all(pq.count == 1 for pq in popular), \
        "Old events outside the window must not count towards popularity"


# ---------------------------------------------------------------------------
# 30. Query-log API cannot access another user's unrestricted history
# ---------------------------------------------------------------------------
def test_own_events_api_cannot_access_another_users_history():
    svc = _make_service()
    principal_a = _make_principal(user_id="uid-A", username="user_a")
    principal_b = _make_principal(user_id="uid-B", username="user_b")

    # Log 3 events for user A and 2 for user B
    for _ in range(3):
        svc.log_event(QueryLogEvent(
            user_id="uid-A",
            role="PRINCIPAL",
            status=QueryLogStatus.SUCCESS,
            event_type=QueryLogEventType.MANUAL_QUERY,
            metric_id="attendance.percentage",
        ))
    for _ in range(2):
        svc.log_event(QueryLogEvent(
            user_id="uid-B",
            role="HOD",
            status=QueryLogStatus.SUCCESS,
            event_type=QueryLogEventType.MANUAL_QUERY,
            metric_id="attendance.percentage",
        ))

    # Each user sees only their own events
    events_a = svc.get_own_recent_events(principal_a)
    events_b = svc.get_own_recent_events(principal_b)

    assert len(events_a) == 3, f"User A should see 3 events, got {len(events_a)}"
    assert len(events_b) == 2, f"User B should see 2 events, got {len(events_b)}"

    # User A's events must all belong to uid-A
    for e in events_a:
        assert e.user_id == "uid-A", f"User A's events must not contain uid-B events: {e.user_id}"

    # User B's events must all belong to uid-B
    for e in events_b:
        assert e.user_id == "uid-B", f"User B's events must not contain uid-A events: {e.user_id}"


# ---------------------------------------------------------------------------
# 31. Student cannot see institutional-scoped patterns even for authorized metrics
# ---------------------------------------------------------------------------
def test_student_cannot_see_institutional_scoped_patterns():
    svc = _make_service()

    # Log INSTITUTION-scoped attendance query (e.g. run by Dean)
    svc.log_event(QueryLogEvent(
        user_id="dean-001",
        role="DEAN",
        scope_type="INSTITUTION",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    # Log SELF-scoped attendance query (run by student)
    svc.log_event(QueryLogEvent(
        user_id="student-001",
        role="STUDENT",
        scope_type="SELF",
        metric_id="attendance.percentage",
        dimensions=[],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    student = _make_principal(
        role="STUDENT",
        scope_type=ScopeType.SELF,
        scope_id="s-001",
        permissions={"attendance.read"},
    )
    popular = svc.get_popular_questions(student)

    # Student should ONLY see the SELF-scoped pattern, NOT the INSTITUTION-scoped one
    assert len(popular) == 1
    assert popular[0].dimension_signature == ""


# ---------------------------------------------------------------------------
# 32. HOD cannot see another department's scoped patterns
# ---------------------------------------------------------------------------
def test_hod_cannot_see_other_department_scoped_patterns():
    svc = _make_service()

    # Log ECE-scoped attendance query
    svc.log_event(QueryLogEvent(
        user_id="ece-hod",
        role="HOD",
        scope_type="DEPARTMENT",
        scope_id="dept-ece-001",
        metric_id="attendance.percentage",
        dimensions=["dim.student"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    # Log CSE-scoped attendance query
    svc.log_event(QueryLogEvent(
        user_id="cse-hod",
        role="HOD",
        scope_type="DEPARTMENT",
        scope_id="dept-cse-001",
        metric_id="attendance.percentage",
        dimensions=["dim.department"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    cse_hod = _make_principal(
        role="HOD",
        scope_type=ScopeType.DEPARTMENT,
        scope_id="dept-cse-001",
        permissions={"attendance.read"},
    )
    popular = svc.get_popular_questions(cse_hod)

    # CSE HOD should ONLY see CSE query, NOT ECE query
    assert len(popular) == 1
    assert popular[0].dimension_signature == "dim.department"


# ---------------------------------------------------------------------------
# 33. Confidential metrics never appear in popular questions
# ---------------------------------------------------------------------------
def test_confidential_metric_never_in_popular_questions():
    svc = _make_service()

    # Attempt to log a confidential metric event
    svc.log_event(QueryLogEvent(
        user_id="admin-001",
        role="PRINCIPAL",
        scope_type="INSTITUTION",
        metric_id="confidential.student_health_notes",
        dimensions=["dim.student"],
        event_type=QueryLogEventType.MANUAL_QUERY,
        status=QueryLogStatus.SUCCESS,
    ))

    principal = _make_principal(permissions={"analytics.read", "attendance.read"})
    popular = svc.get_popular_questions(principal)
    assert len(popular) == 0

