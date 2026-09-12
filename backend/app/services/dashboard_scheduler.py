"""Agent 63 - Phase 12: In-Process Dashboard Refresh Scheduler
Provides lightweight, bounded scheduled refresh execution for role-based dashboards.

CRITICAL SECURITY & RELIABILITY INVARIANTS:
1. Scheduled refresh does NOT bypass authorization: re-resolves and re-verifies the user
   identity and active status on every execution turn.
2. Enforces minimum 60-minute interval to prevent database connection spikes and DoS.
3. Maximum 5 schedules per user and 50 system-wide to bound memory and thread consumption.
4. Clean lifecycle management: graceful startup and cancellation upon application shutdown.
5. Zero raw SQL. Zero stored database credentials. Zero database writes.
"""

import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.schemas.dashboard import DashboardScheduleItem
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.dashboard_registry import (
    DashboardRegistryService,
    get_dashboard_registry_service,
)
from backend.app.services.dashboard_service import (
    DashboardService,
    get_dashboard_service,
)
from backend.app.services.identity_repository import (
    IdentityRepository,
    get_identity_repository,
)

logger = get_logger("agent63.services.scheduler")


class DashboardSchedulerService:
    """In-process background scheduler for role-based dashboard refreshes."""

    def __init__(
        self,
        dashboard_service: Optional[DashboardService] = None,
        registry: Optional[DashboardRegistryService] = None,
        identity_repo: Optional[IdentityRepository] = None,
    ):
        self._dashboard_service = dashboard_service or get_dashboard_service()
        self._registry = registry or get_dashboard_registry_service()
        self._identity_repo = identity_repo or get_identity_repository()

        self._schedules: Dict[str, DashboardScheduleItem] = {}
        self._lock = threading.RLock()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._check_interval_seconds = 10.0  # Polling interval for due schedules

    def start(self) -> None:
        """Starts the scheduler background worker thread."""
        with self._lock:
            if not settings.DASHBOARD_SCHEDULER_ENABLED:
                logger.info("Dashboard scheduler is disabled in application settings.")
                return

            if self._worker_thread and self._worker_thread.is_alive():
                logger.debug("Dashboard scheduler thread is already running.")
                return

            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="agent63-dashboard-scheduler",
                daemon=True,
            )
            self._worker_thread.start()
            logger.info("Dashboard scheduler worker thread started successfully.")

    def stop(self) -> None:
        """Stops the scheduler thread gracefully."""
        with self._lock:
            if not self._worker_thread or not self._worker_thread.is_alive():
                return

            logger.info("Signaling dashboard scheduler to stop...")
            self._stop_event.set()
            self._worker_thread.join(timeout=5.0)
            self._worker_thread = None
            logger.info("Dashboard scheduler stopped successfully.")

    @property
    def is_running(self) -> bool:
        """Returns whether the scheduler worker thread is actively running."""
        with self._lock:
            return bool(self._worker_thread and self._worker_thread.is_alive())

    def create_schedule(
        self,
        principal: AuthenticatedPrincipal,
        dashboard_id: str,
        interval_minutes: int = 60,
    ) -> DashboardScheduleItem:
        """
        Creates and registers a new scheduled refresh job for an authorized dashboard.
        Validates:
        - Principal active status.
        - Minimum interval enforcement (>= 60 minutes).
        - User and system capacity limits.
        - Role authorization for the dashboard.
        - Duplicate schedule prevention.
        """
        if not principal.is_active:
            raise AuthorizationError("Account is inactive or disabled.")

        min_interval = settings.DASHBOARD_SCHEDULE_MIN_INTERVAL_MINUTES
        if interval_minutes < min_interval:
            raise ValueError(
                f"Schedule interval of {interval_minutes} minutes violates minimum allowed interval of {min_interval} minutes."
            )

        # Validate dashboard exists and principal has role
        defn = self._registry.get_dashboard_definition(dashboard_id)
        if not defn:
            raise AuthorizationError(f"Dashboard '{dashboard_id}' does not exist.")

        user_roles_upper = {r.upper() for r in principal.roles}
        allowed_roles_upper = {r.upper() for r in defn.allowed_roles}
        if not (user_roles_upper & allowed_roles_upper):
            raise AuthorizationError(
                f"User role is not authorized to schedule dashboard '{dashboard_id}'."
            )

        with self._lock:
            # Capacity checks
            user_schedules = [
                s for s in self._schedules.values()
                if s.user_id == principal.user_id and s.is_active
            ]
            if len(user_schedules) >= settings.DASHBOARD_MAX_SCHEDULES_PER_USER:
                raise ValueError(
                    f"Maximum active schedules per user ({settings.DASHBOARD_MAX_SCHEDULES_PER_USER}) exceeded."
                )

            active_total = len([s for s in self._schedules.values() if s.is_active])
            if active_total >= settings.DASHBOARD_MAX_TOTAL_SCHEDULES:
                raise ValueError(
                    f"Maximum system-wide active schedules ({settings.DASHBOARD_MAX_TOTAL_SCHEDULES}) reached."
                )

            # Check for existing duplicate schedule for this user and dashboard
            for s in user_schedules:
                if s.dashboard_id == dashboard_id:
                    # Update existing schedule interval
                    s.interval_minutes = interval_minutes
                    s.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
                    logger.info(
                        f"Updated existing schedule '{s.schedule_id}' for user='{principal.username}' "
                        f"dashboard='{dashboard_id}' interval={interval_minutes}m"
                    )
                    return s

            # Create new schedule item
            now = datetime.now(timezone.utc)
            schedule_id = str(uuid.uuid4())
            item = DashboardScheduleItem(
                schedule_id=schedule_id,
                dashboard_id=dashboard_id,
                dashboard_title=defn.title,
                user_id=principal.user_id,
                role=defn.default_role,
                interval_minutes=interval_minutes,
                created_at=now,
                next_run_at=now + timedelta(minutes=interval_minutes),
                is_active=True,
                last_status="SCHEDULED",
            )
            self._schedules[schedule_id] = item
            logger.info(
                f"Created refresh schedule '{schedule_id}' for user='{principal.username}' "
                f"dashboard='{dashboard_id}' interval={interval_minutes}m"
            )
            return item

    def list_schedules(self, principal: AuthenticatedPrincipal) -> List[DashboardScheduleItem]:
        """Returns active refresh schedules owned by the current authenticated principal."""
        with self._lock:
            # Strictly filter to the current user's schedules (no cross-user leakage)
            return [
                s for s in self._schedules.values()
                if s.user_id == principal.user_id and s.is_active
            ]

    def cancel_schedule(self, schedule_id: str, principal: AuthenticatedPrincipal) -> bool:
        """Cancels a scheduled refresh job owned by the authenticated principal."""
        with self._lock:
            schedule = self._schedules.get(schedule_id)
            if not schedule:
                return False

            # Verify ownership
            if schedule.user_id != principal.user_id and not principal.has_role("ADMIN"):
                raise AuthorizationError("Cannot cancel a schedule owned by another institutional user.")

            schedule.is_active = False
            schedule.last_status = "CANCELLED"
            logger.info(f"Cancelled refresh schedule '{schedule_id}' for user='{principal.username}'")
            return True

    def _worker_loop(self) -> None:
        """Background thread execution loop checking for due dashboard schedules."""
        logger.info("Dashboard scheduler worker loop entered.")
        while not self._stop_event.is_set():
            try:
                self._process_due_schedules()
            except Exception as e:
                logger.error(f"Unexpected error in dashboard scheduler loop: {e}", exc_info=True)

            self._stop_event.wait(timeout=self._check_interval_seconds)
        logger.info("Dashboard scheduler worker loop exited.")

    def _process_due_schedules(self) -> None:
        """Identifies and triggers due schedules with strict re-authorization."""
        now = datetime.now(timezone.utc)
        due_schedules: List[DashboardScheduleItem] = []

        with self._lock:
            for s in self._schedules.values():
                if s.is_active and s.next_run_at and s.next_run_at <= now:
                    due_schedules.append(s)

        for schedule in due_schedules:
            self._execute_scheduled_refresh(schedule)

    def _execute_scheduled_refresh(self, schedule: DashboardScheduleItem) -> None:
        """
        Executes a single scheduled dashboard refresh.
        Guarantees:
        - Fresh re-resolution of principal from identity repository.
        - Deactivated accounts fail closed immediately.
        - Full execution through standard dashboard pipeline.
        - Updates next_run_at and last_run_at.
        """
        now = datetime.now(timezone.utc)
        logger.info(
            f"Executing scheduled refresh for schedule='{schedule.schedule_id}' "
            f"dashboard='{schedule.dashboard_id}' user_id='{schedule.user_id}'"
        )

        # 1. Fresh Principal Re-Resolution
        principal = self._identity_repo.resolve_principal(schedule.user_id)
        if not principal or not principal.is_active:
            logger.warning(
                f"Scheduled refresh aborted: user '{schedule.user_id}' is no longer active or found. Deactivating schedule."
            )
            with self._lock:
                schedule.is_active = False
                schedule.last_status = "USER_INACTIVE_OR_REVOKED"
            return

        # 2. Re-verify Dashboard Authorization
        defn = self._registry.get_dashboard_definition(schedule.dashboard_id)
        if not defn:
            with self._lock:
                schedule.is_active = False
                schedule.last_status = "DASHBOARD_NOT_FOUND"
            return

        user_roles_upper = {r.upper() for r in principal.roles}
        allowed_roles_upper = {r.upper() for r in defn.allowed_roles}
        if not (user_roles_upper & allowed_roles_upper):
            logger.warning(
                f"Scheduled refresh aborted: user '{principal.username}' no longer holds authorized role for dashboard '{schedule.dashboard_id}'."
            )
            with self._lock:
                schedule.is_active = False
                schedule.last_status = "ROLE_REVOKED"
            return

        # 3. Execute Dashboard with force_refresh=True
        try:
            resp = self._dashboard_service.get_dashboard(
                dashboard_id=schedule.dashboard_id,
                principal=principal,
                force_refresh=True,
            )
            with self._lock:
                schedule.last_run_at = now
                schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
                schedule.last_status = f"SUCCESS ({resp.refresh_status})"
            logger.info(
                f"Scheduled refresh completed successfully for dashboard='{schedule.dashboard_id}' (status={resp.refresh_status})"
            )
        except Exception as e:
            logger.error(f"Scheduled refresh execution failed for schedule='{schedule.schedule_id}': {e}")
            with self._lock:
                schedule.last_run_at = now
                schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
                schedule.last_status = f"FAILED: {str(e)[:50]}"


_singleton_scheduler: Optional[DashboardSchedulerService] = None


def get_dashboard_scheduler_service() -> DashboardSchedulerService:
    """Dependency provider for DashboardSchedulerService."""
    global _singleton_scheduler
    if _singleton_scheduler is None:
        _singleton_scheduler = DashboardSchedulerService()
    return _singleton_scheduler
