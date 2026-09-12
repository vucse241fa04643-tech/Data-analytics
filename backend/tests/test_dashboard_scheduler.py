"""Agent 63 - Phase 12: Dashboard Refresh Scheduler Tests

Verifies:
1. Schedule creation with valid interval (>= 60 minutes).
2. Interval < 60 minutes rejected with ValueError.
3. Schedule creation for unauthorized dashboard rejected.
4. Duplicate schedule for same user and dashboard updates existing schedule.
5. Max schedules per user limit strictly enforced.
6. List schedules returns strictly current user's schedules (zero cross-user leakage).
7. Cancel schedule deactivates schedule.
8. Scheduler startup and shutdown lifecycle.
9. Worker execution re-authorizes principal on trigger (deactivated user fails closed).
10. CRITICAL SECURITY: Zero raw SQL, zero credentials stored.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from backend.app.core.errors import AuthorizationError
from backend.app.schemas.dashboard import DashboardScheduleItem
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.dashboard_scheduler import (
    DashboardSchedulerService,
    get_dashboard_scheduler_service,
)


@pytest.fixture
def scheduler():
    sched = DashboardSchedulerService()
    # Reset internal schedules for clean test runs
    sched._schedules.clear()
    return sched


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
        permissions={"analytics.read", "attendance.read"},
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
        permissions={"attendance.read"},
    )


# 1. Schedule creation with valid interval
def test_create_schedule_valid(scheduler, principal_user):
    item = scheduler.create_schedule(
        principal=principal_user,
        dashboard_id="principal_executive",
        interval_minutes=60,
    )
    assert item.dashboard_id == "principal_executive"
    assert item.user_id == principal_user.user_id
    assert item.interval_minutes == 60
    assert item.is_active is True
    assert item.next_run_at is not None


# 2. Interval < 60 minutes rejected
def test_create_schedule_sub_60_interval_rejected(scheduler, principal_user):
    with pytest.raises(ValueError) as exc:
        scheduler.create_schedule(
            principal=principal_user,
            dashboard_id="principal_executive",
            interval_minutes=30,  # Below 60 min minimum
        )
    assert "minimum allowed interval of 60 minutes" in str(exc.value)


# 3. Schedule creation for unauthorized dashboard rejected
def test_create_schedule_unauthorized_dashboard_rejected(scheduler, student_user):
    with pytest.raises(AuthorizationError) as exc:
        scheduler.create_schedule(
            principal=student_user,
            dashboard_id="principal_executive",  # Student cannot schedule Principal dashboard
            interval_minutes=60,
        )
    assert "not authorized" in str(exc.value).lower()


# 4. Duplicate schedule updates interval
def test_duplicate_schedule_updates_existing(scheduler, principal_user):
    item1 = scheduler.create_schedule(principal_user, "principal_executive", 60)
    item2 = scheduler.create_schedule(principal_user, "principal_executive", 120)

    assert item1.schedule_id == item2.schedule_id
    assert item2.interval_minutes == 120


# 5. User schedule capacity limit enforced
def test_user_schedule_limit_enforced(scheduler, principal_user):
    scheduler._schedules.clear()
    now = datetime.now(timezone.utc)
    for i in range(5):
        sched_id = f"sched-{i}"
        scheduler._schedules[sched_id] = DashboardScheduleItem(
            schedule_id=sched_id,
            dashboard_id=f"principal_executive_{i}",
            dashboard_title="Test Dashboard",
            user_id=principal_user.user_id,
            role="PRINCIPAL",
            interval_minutes=60,
            created_at=now,
            is_active=True,
        )

    with pytest.raises(ValueError) as exc:
        scheduler.create_schedule(principal_user, "principal_executive", 60)
    assert "Maximum active schedules per user" in str(exc.value)


# 6. List schedules returns only current user's schedules (no cross-user leakage)
def test_list_schedules_user_isolation(scheduler, principal_user, student_user):
    scheduler.create_schedule(principal_user, "principal_executive", 60)
    scheduler.create_schedule(student_user, "student_self", 120)

    prin_schedules = scheduler.list_schedules(principal_user)
    stud_schedules = scheduler.list_schedules(student_user)

    assert len(prin_schedules) == 1
    assert prin_schedules[0].dashboard_id == "principal_executive"

    assert len(stud_schedules) == 1
    assert stud_schedules[0].dashboard_id == "student_self"


# 7. Cancel schedule deactivates schedule
def test_cancel_schedule(scheduler, principal_user):
    item = scheduler.create_schedule(principal_user, "principal_executive", 60)
    cancelled = scheduler.cancel_schedule(item.schedule_id, principal_user)

    assert cancelled is True
    assert item.is_active is False
    assert item.last_status == "CANCELLED"

    # Listing schedules should now be empty
    assert len(scheduler.list_schedules(principal_user)) == 0


# 8. Scheduler startup and clean shutdown
def test_scheduler_lifecycle(scheduler):
    assert scheduler.is_running is False
    # Temporarily enable the scheduler setting for this lifecycle test only.
    # The default is False to prevent background threads during the test suite;
    # production enables it via DASHBOARD_SCHEDULER_ENABLED=true in .env.
    with patch("backend.app.services.dashboard_scheduler.settings") as mock_settings:
        mock_settings.DASHBOARD_SCHEDULER_ENABLED = True
        scheduler.start()
        assert scheduler.is_running is True
        scheduler.stop()
        assert scheduler.is_running is False


# 9. Worker execution re-authorizes principal (deactivated user fails closed)
def test_worker_deactivated_user_fails_closed(scheduler, principal_user):
    item = scheduler.create_schedule(principal_user, "principal_executive", 60)

    # Mock identity repository returning inactive principal
    mock_inactive = principal_user.model_copy()
    mock_inactive.is_active = False

    with patch.object(scheduler._identity_repo, "resolve_principal", return_value=mock_inactive):
        scheduler._execute_scheduled_refresh(item)

    assert item.is_active is False
    assert item.last_status == "USER_INACTIVE_OR_REVOKED"


# 10. CRITICAL SECURITY: Zero raw SQL or credentials stored
def test_scheduler_zero_sql_or_credentials(scheduler, principal_user):
    item = scheduler.create_schedule(principal_user, "principal_executive", 60)
    item_dict = item.model_dump()

    # Ensure no credentials or SQL leaked into schedule object
    forbidden_keys = ["password", "token", "secret", "sql", "query", "db_host", "db_user"]
    for k in forbidden_keys:
        assert k not in item_dict
