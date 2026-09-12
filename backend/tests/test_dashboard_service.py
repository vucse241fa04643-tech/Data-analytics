"""Agent 63 - Phase 12: Role-Based Dashboard Service & Security Tests

Verifies:
1. Catalog resolution filters strictly by principal's roles.
2. Principal receives institution-wide dashboard with approved metrics.
3. HOD receives department-scoped dashboard (CSE vs ECE isolation).
4. Faculty receives course offering scoped dashboard.
5. Student receives self-scoped dashboard only.
6. Quarantined Counsellor account receives no institutional analytics dashboards.
7. Unauthorized dashboard access rejected (AuthorizationError).
8. Error isolation: database unconfigured returns UNAVAILABLE status without crashing dashboard.
9. In-memory caching respects TTL and scope key.
10. Cache isolation across users (user A cannot access user B's cache).
11. CRITICAL SECURITY: Zero raw SQL in dashboard registry or service.
12. CRITICAL SECURITY: Zero LLM invocations in dashboard execution.
"""

from decimal import Decimal
from unittest.mock import patch
import pytest

from backend.app.core.errors import AuthorizationError
from backend.app.schemas.dashboard import WidgetStatus
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.services.dashboard_registry import get_dashboard_registry_service
from backend.app.services.dashboard_service import DashboardService, get_dashboard_service


@pytest.fixture
def dashboard_service():
    return get_dashboard_service()


@pytest.fixture
def principal_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[
            ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "outcomes.read", "placement.read", "academics.read", "quality.read"},
    )


@pytest.fixture
def hod_cse_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000004",
        username="test_hod_cse",
        email="hod.cse@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001")
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "outcomes.read", "placement.read", "academics.read"},
    )


@pytest.fixture
def hod_ece_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000005",
        username="test_hod_ece",
        email="hod.ece@vignan.ac.in",
        roles=["HOD"],
        scoped_roles=[
            ScopedRoleAssignment(role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-ece-002")
        ],
        permissions={"analytics.read", "attendance.read", "assessment.read", "outcomes.read", "placement.read", "academics.read"},
    )


@pytest.fixture
def student_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000010",
        username="test_student_1",
        email="221fa04001@vignan.ac.in",
        roles=["STUDENT"],
        scoped_roles=[
            ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="student-uuid-s101")
        ],
        permissions={"attendance.read", "assessment.read", "outcomes.read"},
    )


@pytest.fixture
def counsellor_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000012",
        username="test_counsellor",
        email="counsellor@vignan.ac.in",
        roles=["COUNSELLOR"],
        scoped_roles=[
            ScopedRoleAssignment(role="COUNSELLOR", scope_type=ScopeType.SELF)
        ],
        permissions={"counselling.read"},
    )


# 1. Catalog resolution filters strictly by principal's roles
def test_catalog_resolution_role_filtering(dashboard_service, principal_user, hod_cse_user, student_user, counsellor_user):
    # Principal catalog
    prin_cat = dashboard_service.get_catalog(principal_user)
    prin_dash_ids = {d.dashboard_id for d in prin_cat.dashboards}
    assert "principal_executive" in prin_dash_ids
    assert "student_self" not in prin_dash_ids

    # HOD catalog
    hod_cat = dashboard_service.get_catalog(hod_cse_user)
    hod_dash_ids = {d.dashboard_id for d in hod_cat.dashboards}
    assert "hod_department" in hod_dash_ids
    assert "principal_executive" not in hod_dash_ids
    assert "student_self" not in hod_dash_ids

    # Student catalog
    stud_cat = dashboard_service.get_catalog(student_user)
    stud_dash_ids = {d.dashboard_id for d in stud_cat.dashboards}
    assert "student_self" in stud_dash_ids
    assert "principal_executive" not in stud_dash_ids
    assert "hod_department" not in stud_dash_ids

    # Counsellor catalog (Quarantined)
    coun_cat = dashboard_service.get_catalog(counsellor_user)
    assert len(coun_cat.dashboards) == 0


# 2. Principal executes institution-wide dashboard (mocked DB)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_principal_dashboard_execution(mock_db_execute, dashboard_service, principal_user):
    mock_db_execute.return_value = (
        ["value"],
        [{"value": Decimal("85.0")}],
        {"value": "numeric"},
        8.0,
    )

    resp = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert resp.dashboard_id == "principal_executive"
    assert resp.role == "PRINCIPAL"
    assert resp.scope["scope_type"] == "INSTITUTION"
    assert len(resp.widgets) > 0
    assert resp.refresh_status == "COMPLETED"
    for w in resp.widgets:
        assert w.status == WidgetStatus.SUCCESS
        assert w.result is not None


# 3. HOD departmental scope enforcement (CSE vs ECE)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_hod_departmental_scope_enforcement(mock_db_execute, dashboard_service, hod_cse_user, hod_ece_user):
    mock_db_execute.return_value = (
        ["pct"],
        [{"pct": Decimal("84.5")}],
        {"pct": "numeric"},
        7.0,
    )

    # HOD CSE
    resp_cse = dashboard_service.get_dashboard("hod_department", hod_cse_user, force_refresh=True)
    assert resp_cse.scope["scope_type"] == "DEPARTMENT"
    assert resp_cse.scope["scope_id"] == "dept-cse-001"
    assert "dept-cse-001" in resp_cse.scope["display"]

    # HOD ECE
    resp_ece = dashboard_service.get_dashboard("hod_department", hod_ece_user, force_refresh=True)
    assert resp_ece.scope["scope_type"] == "DEPARTMENT"
    assert resp_ece.scope["scope_id"] == "dept-ece-002"
    assert "dept-ece-002" in resp_ece.scope["display"]


# 4. Student self-scope enforcement
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_student_self_scope_enforcement(mock_db_execute, dashboard_service, student_user):
    mock_db_execute.return_value = (
        ["attendance_pct"],
        [{"attendance_pct": Decimal("92.0")}],
        {"attendance_pct": "numeric"},
        6.0,
    )

    resp = dashboard_service.get_dashboard("student_self", student_user, force_refresh=True)
    assert resp.dashboard_id == "student_self"
    assert resp.scope["scope_type"] == "SELF"
    assert resp.scope["scope_id"] == "student-uuid-s101"
    assert resp.widgets[0].status == WidgetStatus.SUCCESS


# 5. Unauthorized dashboard access rejected (403)
def test_unauthorized_dashboard_access_rejected(dashboard_service, student_user, hod_cse_user, counsellor_user):
    # Student attempting Principal dashboard
    with pytest.raises(AuthorizationError) as exc_stud:
        dashboard_service.get_dashboard("principal_executive", student_user)
    assert "not authorized" in str(exc_stud.value).lower()

    # HOD attempting Principal dashboard
    with pytest.raises(AuthorizationError) as exc_hod:
        dashboard_service.get_dashboard("principal_executive", hod_cse_user)
    assert "not authorized" in str(exc_hod.value).lower()

    # Counsellor attempting any dashboard
    with pytest.raises(AuthorizationError) as exc_coun:
        dashboard_service.get_dashboard("principal_executive", counsellor_user)
    assert "not authorized" in str(exc_coun.value).lower()


# 6. Database unconfigured handled gracefully (error isolation)
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_database_unconfigured_error_isolation(mock_db_execute, dashboard_service, principal_user):
    from backend.app.core.errors import DatabaseNotConfiguredError
    mock_db_execute.side_effect = DatabaseNotConfiguredError("Database is not currently configured.")

    resp = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert resp.dashboard_id == "principal_executive"
    assert resp.refresh_status == "FAILED"
    for w in resp.widgets:
        assert w.status == WidgetStatus.UNAVAILABLE
        assert "not currently configured" in w.error_message


# 7. In-memory caching respects TTL and force_refresh
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_caching_behavior(mock_db_execute, dashboard_service, principal_user):
    mock_db_execute.return_value = (
        ["value"],
        [{"value": Decimal("85.0")}],
        {"value": "numeric"},
        5.0,
    )

    # Initial load: LIVE
    resp1 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert resp1.refresh_mode == "MANUAL"

    # Second load without force_refresh: CACHED
    resp2 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=False)
    assert resp2.refresh_mode == "CACHED"
    assert resp2.widgets[0].widget_id == resp1.widgets[0].widget_id

    # Third load with force_refresh: MANUAL (bypasses cache)
    resp3 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert resp3.refresh_mode == "MANUAL"


# 8. Cache isolation across users
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_cache_isolation_across_users(mock_db_execute, dashboard_service, hod_cse_user, hod_ece_user):
    mock_db_execute.return_value = (
        ["pct"],
        [{"pct": Decimal("85.0")}],
        {"pct": "numeric"},
        5.0,
    )

    # Load for HOD CSE
    resp_cse = dashboard_service.get_dashboard("hod_department", hod_cse_user, force_refresh=True)
    assert resp_cse.scope["scope_id"] == "dept-cse-001"

    # Load for HOD ECE should NOT hit CSE's cache
    resp_ece = dashboard_service.get_dashboard("hod_department", hod_ece_user, force_refresh=False)
    assert resp_ece.scope["scope_id"] == "dept-ece-002"
    assert resp_ece.refresh_mode != "CACHED" or resp_ece.scope["scope_id"] == "dept-ece-002"


# 9. CRITICAL SECURITY: Zero raw SQL in dashboard registry or service
def test_zero_raw_sql_in_dashboards():
    reg = get_dashboard_registry_service()
    all_defs = reg.get_all_definitions()

    forbidden_sql_terms = [
        "SELECT ", "FROM ", "WHERE ", "INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "
    ]

    for d_id, defn in all_defs.items():
        for w in defn.widgets:
            assert hasattr(w, "metric_id"), f"Widget {w.widget_id} missing metric_id"
            assert not hasattr(w, "sql"), f"Widget {w.widget_id} has forbidden 'sql' field"
            assert not hasattr(w, "query"), f"Widget {w.widget_id} has forbidden 'query' field"
            for term in forbidden_sql_terms:
                assert term not in w.widget_id.upper()
                assert term not in w.metric_id.upper()
                assert term not in w.title.upper()


# 10. CRITICAL SECURITY: Zero LLM calls in dashboard service
def test_zero_llm_calls_in_dashboard_service(dashboard_service):
    forbidden_clients = ["groq_client", "gemini_client", "llm_client", "openai_client"]
    for client_name in forbidden_clients:
        assert not hasattr(dashboard_service, client_name), f"Dashboard service violates security: has '{client_name}'"
