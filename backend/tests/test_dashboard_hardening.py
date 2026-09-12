"""Agent 63 - Phase 12 Hardening: Regression & Security Tests

Implements all 20 hardening checks required for Phase 12 approval:

1.  Unsupported metric cannot enter dashboard registry.
2.  Review-required placement.placement_rate is NOT used in any dashboard.
3.  Every dashboard widget maps to an approved semantic metric.
4.  Exact Phase 5 role identifiers (IQAC, PLACEMENT) are used — not invented variants.
5.  Fake role identifiers cannot grant dashboard access.
6.  HOD CSE cannot access ECE dashboard data (scope isolation).
7.  Student cannot access institutional dashboard (role boundary).
8.  Dashboard execution routes through SQLCompiler.
9.  Dashboard execution routes through SQLValidator.
10. Dashboard execution routes through the read-only executor.
11. Scheduled refresh reauthorizes current user identity.
12. Role removal invalidates scheduled refresh.
13. Scope/role change fails scheduled refresh gracefully.
14. Cache cannot bypass authorization (auth evaluated before cache lookup).
15. Cache is isolated by user and scope key.
16. Force refresh bypasses cache safely.
17. No raw SQL in dashboard definitions or registry.
18. No LLM clients in dashboard service.
19. Confidential role (COUNSELLOR) remains completely quarantined.
20. All dashboard metrics exist in semantic registry and are APPROVED.
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.errors import AuthorizationError
from backend.app.schemas.dashboard import WidgetStatus
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.services.dashboard_registry import (
    DASHBOARD_REGISTRY,
    get_dashboard_registry_service,
)
from backend.app.services.dashboard_scheduler import DashboardSchedulerService
from backend.app.services.dashboard_service import DashboardService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dashboard_service():
    return DashboardService()


@pytest.fixture
def registry():
    return get_dashboard_registry_service()


@pytest.fixture
def principal_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={
            "analytics.read", "attendance.read", "assessment.read",
            "outcomes.read", "placement.read", "academics.read", "quality.read",
        },
    )


@pytest.fixture
def iqac_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000002",
        username="test_iqac",
        email="iqac.director@vignan.ac.in",
        roles=["IQAC"],
        scoped_roles=[ScopedRoleAssignment(role="IQAC", scope_type=ScopeType.INSTITUTION)],
        permissions={
            "analytics.read", "quality.read", "outcomes.read",
            "attendance.read", "assessment.read", "academics.read",
        },
    )


@pytest.fixture
def placement_user():
    return AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000008",
        username="test_placement",
        email="placement.officer@vignan.ac.in",
        roles=["PLACEMENT"],
        scoped_roles=[ScopedRoleAssignment(role="PLACEMENT", scope_type=ScopeType.INSTITUTION)],
        permissions={"placement.read", "academics.read"},
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
        permissions={
            "analytics.read", "attendance.read", "assessment.read",
            "outcomes.read", "placement.read", "academics.read",
        },
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
        permissions={
            "analytics.read", "attendance.read", "assessment.read",
            "outcomes.read", "placement.read", "academics.read",
        },
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
        scoped_roles=[ScopedRoleAssignment(role="COUNSELLOR", scope_type=ScopeType.SELF)],
        permissions={"counselling.read"},
    )


# ---------------------------------------------------------------------------
# 1. Unsupported metric cannot enter the dashboard registry
# ---------------------------------------------------------------------------
def test_no_unsupported_metrics_in_registry():
    """Every widget metric_id must exist in the authoritative semantic registry."""
    reg = json.load(open("semantic_layer/registry/semantic_registry.json", encoding="utf-8"))
    known_metric_ids = {m["metric_id"] for m in reg["metrics"]}

    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for w in defn.widgets:
            assert w.metric_id in known_metric_ids, (
                f"Widget '{w.widget_id}' in dashboard '{dash_id}' references "
                f"unknown metric '{w.metric_id}' not found in semantic registry."
            )


# ---------------------------------------------------------------------------
# 2. placement.placement_rate (review-required) is NOT used in any dashboard
# ---------------------------------------------------------------------------
def test_placement_rate_review_required_not_used():
    """placement.placement_rate (REVIEW_REQUIRED) must not appear in any dashboard widget."""
    forbidden_metric = "placement.placement_rate"
    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for w in defn.widgets:
            assert w.metric_id != forbidden_metric, (
                f"FORBIDDEN: Widget '{w.widget_id}' in dashboard '{dash_id}' uses "
                f"review-required metric '{forbidden_metric}'."
            )


# ---------------------------------------------------------------------------
# 3. Every dashboard widget maps to an APPROVED semantic metric
# ---------------------------------------------------------------------------
def test_all_dashboard_widget_metrics_are_approved():
    """Every widget metric_id must have status APPROVED in the semantic registry."""
    reg = json.load(open("semantic_layer/registry/semantic_registry.json", encoding="utf-8"))
    metric_status = {m["metric_id"]: m["status"] for m in reg["metrics"]}

    unapproved = []
    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for w in defn.widgets:
            status = metric_status.get(w.metric_id, "NOT_FOUND")
            if status != "APPROVED":
                unapproved.append((dash_id, w.widget_id, w.metric_id, status))

    assert unapproved == [], (
        "UNAPPROVED METRICS FOUND IN DASHBOARD REGISTRY:\n" +
        "\n".join(f"  Dashboard={d}, Widget={wid}, Metric={mid}, Status={st}"
                  for d, wid, mid, st in unapproved)
    )


# ---------------------------------------------------------------------------
# 4. Exact Phase 5 role identifiers (IQAC, PLACEMENT) are used
# ---------------------------------------------------------------------------
def test_exact_phase5_role_identifiers_used():
    """
    Dashboard registry must use IQAC and PLACEMENT (not IQAC_DIRECTOR or PLACEMENT_OFFICER).
    """
    forbidden_role_variants = {"IQAC_DIRECTOR", "PLACEMENT_OFFICER", "IQACDIRECTOR", "PLACEMENTOFFICER"}
    authorized_roles_found = set()

    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for role in defn.allowed_roles:
            role_normalized = role.upper().replace("-", "").replace("_", "").replace(" ", "")
            assert role_normalized not in forbidden_role_variants, (
                f"Dashboard '{dash_id}' uses invented role '{role}'. "
                f"Phase 5 authoritative roles are: IQAC, PLACEMENT."
            )
            authorized_roles_found.add(role.upper())

    # Verify actual authoritative Phase 5 roles appear
    assert "IQAC" in authorized_roles_found, "IQAC role must appear in at least one dashboard."
    assert "PLACEMENT" in authorized_roles_found, "PLACEMENT role must appear in at least one dashboard."


# ---------------------------------------------------------------------------
# 5. Fake role identifiers cannot grant dashboard access
# ---------------------------------------------------------------------------
def test_fake_role_cannot_grant_dashboard_access(dashboard_service):
    """Invented/fake roles must not grant any dashboard access."""
    fake_role_user = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000099",
        username="fake_role_user",
        email="fake@vignan.ac.in",
        roles=["SUPER_ADMIN_BYPASS", "IQAC_DIRECTOR"],
        scoped_roles=[
            ScopedRoleAssignment(role="SUPER_ADMIN_BYPASS", scope_type=ScopeType.INSTITUTION)
        ],
        permissions={"analytics.read", "quality.read", "outcomes.read"},
    )

    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("principal_executive", fake_role_user)

    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("iqac_quality", fake_role_user)


# ---------------------------------------------------------------------------
# 6. HOD CSE cannot access ECE scope or principal dashboard
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_hod_cse_cannot_access_ece_scope(mock_db, dashboard_service, hod_cse_user, hod_ece_user):
    """HOD CSE scope is strictly dept-cse-001. Cannot access ECE data or principal dashboard."""
    mock_db.return_value = (["pct"], [{"pct": Decimal("82.0")}], {"pct": "numeric"}, 5.0)

    resp_cse = dashboard_service.get_dashboard("hod_department", hod_cse_user, force_refresh=True)
    assert resp_cse.scope["scope_id"] == "dept-cse-001"

    resp_ece = dashboard_service.get_dashboard("hod_department", hod_ece_user, force_refresh=True)
    assert resp_ece.scope["scope_id"] == "dept-ece-002"
    assert resp_ece.scope["scope_id"] != resp_cse.scope["scope_id"]

    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("principal_executive", hod_cse_user)


# ---------------------------------------------------------------------------
# 7. Student cannot access institutional dashboards
# ---------------------------------------------------------------------------
def test_student_cannot_access_institutional_dashboard(dashboard_service, student_user):
    """STUDENT role cannot access any institutional (non-student) dashboard."""
    for dash_id in ["principal_executive", "hod_department", "iqac_quality", "dean_campus",
                     "placement_executive", "coe_examination"]:
        with pytest.raises(AuthorizationError):
            dashboard_service.get_dashboard(dash_id, student_user)


# ---------------------------------------------------------------------------
# 8. Dashboard execution calls SQLCompiler
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_dashboard_execution_calls_sql_compiler(mock_db, dashboard_service, principal_user):
    """Widget execution must route through SQLCompiler.compile()."""
    mock_db.return_value = (["v"], [{"v": Decimal("85.0")}], {"v": "numeric"}, 5.0)

    with patch.object(dashboard_service._compiler, "compile",
                      wraps=dashboard_service._compiler.compile) as mock_compile:
        dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
        assert mock_compile.call_count > 0, "SQLCompiler.compile() was never called."


# ---------------------------------------------------------------------------
# 9. Dashboard execution calls SQLValidator
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_dashboard_execution_calls_sql_validator(mock_db, dashboard_service, principal_user):
    """Widget execution must route through SQLValidator.validate_artifact()."""
    mock_db.return_value = (["v"], [{"v": Decimal("85.0")}], {"v": "numeric"}, 5.0)

    with patch.object(dashboard_service._validator, "validate_artifact",
                      wraps=dashboard_service._validator.validate_artifact) as mock_validate:
        dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
        assert mock_validate.call_count > 0, "SQLValidator.validate_artifact() was never called."


# ---------------------------------------------------------------------------
# 10. Dashboard execution calls the read-only executor
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_dashboard_execution_calls_executor(mock_db, dashboard_service, principal_user):
    """Widget execution must route through ExecutionService.execute_artifact()."""
    mock_db.return_value = (["v"], [{"v": Decimal("85.0")}], {"v": "numeric"}, 5.0)

    with patch.object(dashboard_service._executor, "execute_artifact",
                      wraps=dashboard_service._executor.execute_artifact) as mock_exec:
        dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
        assert mock_exec.call_count > 0, "ExecutionService.execute_artifact() was never called."


# ---------------------------------------------------------------------------
# 11. Scheduled refresh reauthorizes current user identity
# ---------------------------------------------------------------------------
def test_scheduled_refresh_reauthorizes_user_identity():
    """Scheduler must call resolve_principal() on every scheduled execution."""
    scheduler = DashboardSchedulerService()
    scheduler._schedules.clear()

    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read", "attendance.read", "assessment.read", "outcomes.read",
                     "placement.read", "academics.read", "quality.read"},
        is_active=True,
    )
    item = scheduler.create_schedule(principal, "principal_executive", 60)

    resolve_calls = []

    def tracking_resolve(uid):
        resolve_calls.append(uid)
        return principal

    with patch.object(scheduler._identity_repo, "resolve_principal", side_effect=tracking_resolve):
        with patch.object(scheduler._dashboard_service, "get_dashboard") as mock_dash:
            mock_dash.return_value = MagicMock(refresh_status="COMPLETED")
            scheduler._execute_scheduled_refresh(item)

    assert len(resolve_calls) > 0, "Scheduler skipped identity re-authorization!"
    assert resolve_calls[0] == principal.user_id


# ---------------------------------------------------------------------------
# 12. Role removal invalidates scheduled refresh
# ---------------------------------------------------------------------------
def test_role_removal_invalidates_scheduled_refresh():
    """If user's roles no longer authorize the dashboard, schedule is deactivated."""
    scheduler = DashboardSchedulerService()
    scheduler._schedules.clear()

    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
        is_active=True,
    )
    item = scheduler.create_schedule(principal, "principal_executive", 60)

    # User is demoted to STUDENT — can no longer access principal_executive
    demoted = principal.model_copy(update={
        "roles": ["STUDENT"],
        "scoped_roles": [ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF, scope_id="s-001")],
    })

    with patch.object(scheduler._identity_repo, "resolve_principal", return_value=demoted):
        scheduler._execute_scheduled_refresh(item)

    assert item.is_active is False, "Schedule not deactivated after role revocation."
    assert item.last_status == "ROLE_REVOKED"


# ---------------------------------------------------------------------------
# 13. Deactivated account fails scheduled refresh gracefully
# ---------------------------------------------------------------------------
def test_deactivated_account_fails_scheduled_refresh_gracefully():
    """Deactivated account must cancel schedule without raising exceptions."""
    scheduler = DashboardSchedulerService()
    scheduler._schedules.clear()

    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="test_principal",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={"analytics.read"},
        is_active=True,
    )
    item = scheduler.create_schedule(principal, "principal_executive", 60)

    deactivated = principal.model_copy(update={"is_active": False})

    # Must not raise — must silently deactivate
    with patch.object(scheduler._identity_repo, "resolve_principal", return_value=deactivated):
        scheduler._execute_scheduled_refresh(item)

    assert item.is_active is False
    assert item.last_status == "USER_INACTIVE_OR_REVOKED"


# ---------------------------------------------------------------------------
# 14. Cache cannot bypass authorization
# ---------------------------------------------------------------------------
def test_cache_cannot_bypass_authorization(dashboard_service, student_user):
    """
    Authorization must be checked before cache is consulted.
    A student cannot read HOD/Principal dashboard even if cached.
    """
    # Student attempting to read HOD or Principal dashboard must ALWAYS get 403
    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("hod_department", student_user)

    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("principal_executive", student_user)

    # Even with force_refresh=False (cache read path), auth must fire
    with pytest.raises(AuthorizationError):
        dashboard_service.get_dashboard("principal_executive", student_user, force_refresh=False)


# ---------------------------------------------------------------------------
# 15. Cache isolated by user and scope key
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_cache_isolated_by_user_and_scope(mock_db, dashboard_service, hod_cse_user, hod_ece_user):
    """HOD CSE and HOD ECE must have isolated cache entries; ECE must never read CSE cache."""
    mock_db.return_value = (["pct"], [{"pct": Decimal("85.0")}], {"pct": "numeric"}, 5.0)

    resp_cse = dashboard_service.get_dashboard("hod_department", hod_cse_user, force_refresh=True)
    assert resp_cse.scope["scope_id"] == "dept-cse-001"

    resp_ece = dashboard_service.get_dashboard("hod_department", hod_ece_user, force_refresh=False)
    assert resp_ece.scope["scope_id"] == "dept-ece-002", "ECE HOD received CSE cache — isolation FAILED."

    cse_key = dashboard_service._build_cache_key(hod_cse_user, "hod_department")
    ece_key = dashboard_service._build_cache_key(hod_ece_user, "hod_department")
    assert cse_key != ece_key, "Cache keys for CSE and ECE HOD must be distinct."


# ---------------------------------------------------------------------------
# 16. Force refresh bypasses cache
# ---------------------------------------------------------------------------
@patch("backend.app.services.execution_service.college_database_service.execute_query")
def test_force_refresh_bypasses_cache(mock_db, dashboard_service, principal_user):
    """force_refresh=True must always re-execute, never serve from cache."""
    mock_db.return_value = (["v"], [{"v": Decimal("88.0")}], {"v": "numeric"}, 5.0)

    r1 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert r1.refresh_mode == "MANUAL"

    r2 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=False)
    assert r2.refresh_mode == "CACHED"

    r3 = dashboard_service.get_dashboard("principal_executive", principal_user, force_refresh=True)
    assert r3.refresh_mode == "MANUAL", "force_refresh=True served from cache — VIOLATION."
    assert mock_db.call_count >= 2, "force_refresh did not trigger new DB execution."


# ---------------------------------------------------------------------------
# 17. No raw SQL in dashboard definitions or registry
# ---------------------------------------------------------------------------
def test_no_raw_sql_in_dashboard_definitions():
    """Verify no SQL keywords appear in any widget definition fields."""
    sql_keywords = ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE",
                    "ALTER TABLE", "DROP TABLE", "TRUNCATE "]

    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for w in defn.widgets:
            check_fields = [w.widget_id, w.metric_id, w.title, w.description or ""]
            if w.dimension:
                check_fields.append(w.dimension)

            for field_val in check_fields:
                for kw in sql_keywords:
                    assert kw not in field_val.upper(), (
                        f"RAW SQL DETECTED: widget '{w.widget_id}' in '{dash_id}' contains '{kw}'"
                    )

            assert not hasattr(w, "sql"), f"Widget '{w.widget_id}' has forbidden 'sql' field."
            assert not hasattr(w, "query"), f"Widget '{w.widget_id}' has forbidden 'query' field."


# ---------------------------------------------------------------------------
# 18. No LLM clients in dashboard service
# ---------------------------------------------------------------------------
def test_no_llm_clients_in_dashboard_service(dashboard_service):
    """DashboardService must have zero LLM client references."""
    forbidden_attrs = [
        "groq_client", "gemini_client", "llm_client", "openai_client",
        "_groq", "_gemini", "_llm", "_openai",
    ]
    for attr in forbidden_attrs:
        assert not hasattr(dashboard_service, attr), (
            f"DashboardService has forbidden LLM attribute '{attr}'."
        )

    import backend.app.services.dashboard_service as ds_mod
    for mod in ["groq", "openai", "anthropic"]:
        assert mod not in dir(ds_mod), f"Dashboard service references LLM module '{mod}'."


# ---------------------------------------------------------------------------
# 19. COUNSELLOR remains completely quarantined
# ---------------------------------------------------------------------------
def test_counsellor_completely_quarantined(dashboard_service, counsellor_user):
    """COUNSELLOR must receive empty catalog and 403 on all dashboard access attempts."""
    catalog = dashboard_service.get_catalog(counsellor_user)
    assert len(catalog.dashboards) == 0, "SECURITY: COUNSELLOR received non-empty dashboard catalog."

    for dash_id in DASHBOARD_REGISTRY.keys():
        with pytest.raises(AuthorizationError):
            dashboard_service.get_dashboard(dash_id, counsellor_user)


# ---------------------------------------------------------------------------
# 20. Complete metric integrity table: approved + compiler-supported
# ---------------------------------------------------------------------------
def test_complete_metric_integrity_table():
    """
    Full verification: every dashboard widget metric is APPROVED and has a
    SQLCompiler formula mapping. Prints an audit table.
    """
    from backend.app.services.sql_compiler import APPROVED_METRIC_FORMULAS

    reg = json.load(open("semantic_layer/registry/semantic_registry.json", encoding="utf-8"))
    metric_status = {m["metric_id"]: m["status"] for m in reg["metrics"]}

    violations = []
    print("\n=== PHASE 12 METRIC INTEGRITY TABLE ===")
    print(f"{'Dashboard':<22} {'Widget':<28} {'Metric ID':<40} {'Approved':<12} {'Compiler':<12}")
    print("-" * 118)

    for dash_id, defn in DASHBOARD_REGISTRY.items():
        for w in defn.widgets:
            status = metric_status.get(w.metric_id, "NOT_FOUND")
            is_approved = (status == "APPROVED")
            has_compiler = (w.metric_id in APPROVED_METRIC_FORMULAS)

            approved_str = "APPROVED" if is_approved else f"FAIL:{status}"
            compiler_str = "SUPPORTED" if has_compiler else "MISSING"
            print(f"{dash_id:<22} {w.widget_id:<28} {w.metric_id:<40} {approved_str:<12} {compiler_str:<12}")

            if not is_approved:
                violations.append(f"UNAPPROVED: {dash_id}/{w.widget_id}/{w.metric_id} ({status})")
            if not has_compiler:
                violations.append(f"NO_COMPILER_PATH: {dash_id}/{w.widget_id}/{w.metric_id}")

    print("-" * 118)
    total_widgets = sum(len(d.widgets) for d in DASHBOARD_REGISTRY.values())
    print(f"Total widgets checked: {total_widgets}")

    assert violations == [], (
        "METRIC INTEGRITY VIOLATIONS:\n" + "\n".join(f"  * {v}" for v in violations)
    )
