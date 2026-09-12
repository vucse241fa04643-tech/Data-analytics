"""Agent 63 - Phase 12: Role-Based Dashboard Execution Service
Orchestrates secure, deterministic dashboard generation, multi-tier authorization,
bounded widget execution, result caching, visualization, and anomaly assessment.

CRITICAL SECURITY INVARIANTS:
1. Dashboard is a presentation layer, NOT an authorization mechanism.
2. Every widget query is authorized against the current authenticated principal.
3. User role and scope are resolved server-side from AuthenticatedPrincipal; never trusted from frontend.
4. Queries execute ONLY via approved semantic catalog metrics through SQLCompiler and AST SQLValidator.
5. Zero raw SQL. Zero LLM calls. Zero database writes.
6. Graceful failure isolation: a failed widget does not compromise the dashboard.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.core.errors import (
    AuthorizationError,
    DatabaseNotConfiguredError,
    SQLAuthorizationError,
    SQLCompilationError,
    SQLValidationError,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.dashboard import (
    DashboardCatalogItem,
    DashboardCatalogResponse,
    DashboardDefinition,
    DashboardResponse,
    DashboardWidgetResult,
    WidgetDefinition,
    WidgetStatus,
)
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType
from backend.app.schemas.query_result import QueryResult, QueryResultStatus
from backend.app.services.anomaly_service import (
    AnomalyDetectionService,
    get_anomaly_service,
)
from backend.app.services.authorization import (
    AuthorizationService,
    get_authorization_service,
)
from backend.app.services.dashboard_registry import (
    DashboardRegistryService,
    get_dashboard_registry_service,
)
from backend.app.services.execution_service import (
    ExecutionService,
    execution_service,
)
from backend.app.services.sql_compiler import (
    SQLCompiler,
    get_sql_compiler,
)
from backend.app.services.sql_validator import (
    SQLValidator,
    get_sql_validator,
)
from backend.app.services.visualization_service import (
    VisualizationService,
    get_visualization_service,
)

logger = get_logger("agent63.services.dashboard")


class DashboardCacheEntry:
    """In-memory cached dashboard response with strict scope binding and TTL."""

    def __init__(self, response: DashboardResponse, expires_at: datetime):
        self.response = response
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


class DashboardService:
    """Central service orchestrating role-based dashboard loading, caching, and execution."""

    def __init__(
        self,
        registry: Optional[DashboardRegistryService] = None,
        authorization: Optional[AuthorizationService] = None,
        compiler: Optional[SQLCompiler] = None,
        validator: Optional[SQLValidator] = None,
        executor: Optional[ExecutionService] = None,
        visualizer: Optional[VisualizationService] = None,
        anomaly_detector: Optional[AnomalyDetectionService] = None,
    ):
        self._registry = registry or get_dashboard_registry_service()
        self._authorization = authorization or get_authorization_service()
        self._compiler = compiler or get_sql_compiler()
        self._validator = validator or get_sql_validator()
        self._executor = executor or execution_service
        self._visualizer = visualizer or get_visualization_service()
        self._anomaly_detector = anomaly_detector or get_anomaly_service()

        self._cache: Dict[str, DashboardCacheEntry] = {}
        self._cache_lock = threading.RLock()

    def _build_cache_key(
        self,
        principal: AuthenticatedPrincipal,
        dashboard_id: str,
    ) -> str:
        """Constructs a tenant-safe cache key bound to user ID, dashboard ID, roles, and scopes."""
        roles_str = ",".join(sorted(principal.roles))
        scopes_str = ",".join(
            sorted(f"{sr.role}:{sr.scope_type}:{sr.scope_id}" for sr in principal.scoped_roles)
        )
        return f"{principal.user_id}::{dashboard_id}::{roles_str}::{scopes_str}"

    def get_catalog(self, principal: AuthenticatedPrincipal) -> DashboardCatalogResponse:
        """Returns the list of dashboards permitted for the authenticated principal's roles."""
        if not principal.is_active:
            raise AuthorizationError("Account is inactive or disabled.")

        matched_definitions = self._registry.get_dashboards_for_roles(principal.roles)
        items: List[DashboardCatalogItem] = []

        for idx, defn in enumerate(matched_definitions):
            items.append(
                DashboardCatalogItem(
                    dashboard_id=defn.dashboard_id,
                    title=defn.title,
                    description=defn.description,
                    role=defn.default_role,
                    widget_count=len(defn.widgets),
                    is_default=(idx == 0),
                )
            )

        active_id = items[0].dashboard_id if items else None
        return DashboardCatalogResponse(
            dashboards=items,
            user_roles=list(principal.roles),
            active_dashboard_id=active_id,
        )

    def get_dashboard(
        self,
        dashboard_id: str,
        principal: AuthenticatedPrincipal,
        force_refresh: bool = False,
    ) -> DashboardResponse:
        """
        Executes and returns a complete role-based dashboard for the authenticated principal.
        Enforces defense-in-depth:
        1. Role verification.
        2. Scope boundary resolution.
        3. Widget-by-widget metric authorization and compilation.
        4. Read-only execution with statement timeout.
        5. Deterministic visualization and anomaly assessment.
        6. Cache isolation.
        """
        if not principal.is_active:
            raise AuthorizationError("Account is inactive or disabled.")

        # 1. Resolve Dashboard Definition
        definition = self._registry.get_dashboard_definition(dashboard_id)
        if not definition:
            raise AuthorizationError(
                message=f"Requested dashboard '{dashboard_id}' does not exist.",
            )

        # 2. Strict Role Verification
        user_roles_upper = {r.upper() for r in principal.roles}
        allowed_roles_upper = {r.upper() for r in definition.allowed_roles}
        if not (user_roles_upper & allowed_roles_upper):
            logger.warning(
                f"Dashboard access denied: user='{principal.username}' roles={principal.roles} "
                f"attempted to access dashboard='{dashboard_id}' (allowed={definition.allowed_roles})"
            )
            raise AuthorizationError(
                message=f"User role is not authorized for dashboard '{dashboard_id}'.",
            )

        # 3. Check Cache if force_refresh is False
        cache_key = self._build_cache_key(principal, dashboard_id)
        if not force_refresh and settings.DASHBOARD_CACHE_ENABLED:
            with self._cache_lock:
                entry = self._cache.get(cache_key)
                if entry and not entry.is_expired:
                    logger.debug(f"Dashboard cache hit for user='{principal.username}' key='{cache_key}'")
                    cached_resp = entry.response.model_copy()
                    cached_resp.refresh_mode = "CACHED"
                    return cached_resp

        # 4. Resolve Effective Scope Details for Presentation Metadata
        effective_scope = self._resolve_presentation_scope(principal, definition)

        # 5. Execute Widgets with Bounded Concurrency & Error Isolation
        widgets = definition.widgets[: settings.DASHBOARD_MAX_WIDGETS_PER_DASHBOARD]
        widget_results = self._execute_widgets_bounded(widgets, principal)

        # 6. Determine Refresh Status
        statuses = {w.status for w in widget_results}
        if all(s == WidgetStatus.SUCCESS for s in statuses):
            refresh_status = "COMPLETED"
        elif any(s == WidgetStatus.SUCCESS for s in statuses):
            refresh_status = "PARTIAL_FAILURE"
        else:
            refresh_status = "FAILED"

        now = datetime.now(timezone.utc)
        response = DashboardResponse(
            dashboard_id=definition.dashboard_id,
            title=definition.title,
            description=definition.description,
            role=definition.default_role,
            scope=effective_scope,
            generated_at=now,
            last_refreshed_at=now,
            refresh_mode="MANUAL" if force_refresh else "LIVE",
            refresh_status=refresh_status,
            widgets=widget_results,
        )

        # 7. Store in Cache
        if settings.DASHBOARD_CACHE_ENABLED:
            with self._cache_lock:
                ttl = timedelta(seconds=settings.DASHBOARD_CACHE_TTL_SECONDS)
                self._cache[cache_key] = DashboardCacheEntry(response, now + ttl)

        return response

    def clear_user_cache(self, user_id: str) -> int:
        """Clears all cached dashboard responses for a specific user."""
        with self._cache_lock:
            to_remove = [k for k in self._cache if k.startswith(f"{user_id}::")]
            for k in to_remove:
                del self._cache[k]
            return len(to_remove)

    def _resolve_presentation_scope(
        self,
        principal: AuthenticatedPrincipal,
        definition: DashboardDefinition,
    ) -> Dict[str, Any]:
        """Resolves human-readable scope metadata derived strictly from backend scoped roles."""
        for sr in principal.scoped_roles:
            if sr.role.upper() in [r.upper() for r in definition.allowed_roles]:
                return {
                    "scope_type": sr.scope_type.value,
                    "scope_id": sr.scope_id,
                    "display": (
                        f"Department: {sr.scope_id}"
                        if sr.scope_type == ScopeType.DEPARTMENT
                        else (
                            f"Campus: {sr.scope_id}"
                            if sr.scope_type == ScopeType.CAMPUS
                            else (
                                f"Offering: {sr.scope_id}"
                                if sr.scope_type == ScopeType.COURSE_OFFERING
                                else (
                                    "Student Personal Scope"
                                    if sr.scope_type == ScopeType.SELF
                                    else "Institution-Wide"
                                )
                            )
                        )
                    ),
                }
        return {"scope_type": "INSTITUTION", "scope_id": None, "display": "Institution-Wide"}

    def _execute_widgets_bounded(
        self,
        widgets: List[WidgetDefinition],
        principal: AuthenticatedPrincipal,
    ) -> List[DashboardWidgetResult]:
        """Executes widgets with bounded concurrency, isolating any partial widget errors."""
        max_workers = min(
            settings.DASHBOARD_MAX_CONCURRENT_WIDGET_EXECUTIONS,
            len(widgets) or 1,
        )

        results_dict: Dict[int, DashboardWidgetResult] = {}

        def _worker(idx: int, widget: WidgetDefinition) -> Tuple[int, DashboardWidgetResult]:
            res = self._execute_single_widget(widget, principal)
            return idx, res

        # Run via bounded ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(_worker, idx, w): idx for idx, w in enumerate(widgets)
            }
            for future in as_completed(future_to_idx):
                idx, res = future.result()
                results_dict[idx] = res

        # Preserve declared display order
        return [results_dict[i] for i in range(len(widgets))]

    def _execute_single_widget(
        self,
        widget: WidgetDefinition,
        principal: AuthenticatedPrincipal,
    ) -> DashboardWidgetResult:
        """
        Executes an individual widget through the secure analytical pipeline:
        Authorization -> SQL Compilation -> AST Validation -> Execution -> Visualization -> Anomaly.
        """
        display_name, unit, _ = self._visualizer._get_metric_meta(widget.metric_id)
        now = datetime.now(timezone.utc)

        # Step 1: Metric Authorization Check
        auth_decision = self._authorization.authorize_metric(principal, widget.metric_id)
        if not auth_decision.allowed:
            return DashboardWidgetResult(
                widget_id=widget.widget_id,
                metric_id=widget.metric_id,
                metric_display_name=display_name,
                title=widget.title,
                visualization_type=widget.visualization_type.value,
                status=WidgetStatus.UNAUTHORIZED,
                error_message=auth_decision.message or "Unauthorized metric for current role.",
                last_updated=now,
            )

        # Step 2: Construct StructuredIntent (server-side scoped)
        dimensions = [widget.dimension] if widget.dimension else []
        intent = StructuredIntent(
            intent_type=IntentType.METRIC_QUERY,
            primary_metric_id=widget.metric_id,
            dimensions=dimensions,
            filters=dict(widget.default_filters),
            reasoning_summary=f"Dashboard widget query: {widget.title}",
        )

        # Step 3: Compile SQL Artifact & Validate AST
        try:
            req_id = f"dash-{uuid.uuid4()}"
            raw_artifact = self._compiler.compile(
                intent=intent,
                principal=principal,
                request_id=req_id,
            )
            validated_artifact = self._validator.validate_artifact(raw_artifact)
        except (SQLAuthorizationError, AuthorizationError) as e:
            logger.info(f"Widget {widget.widget_id} authorization error: {e}")
            return DashboardWidgetResult(
                widget_id=widget.widget_id,
                metric_id=widget.metric_id,
                metric_display_name=display_name,
                title=widget.title,
                visualization_type=widget.visualization_type.value,
                status=WidgetStatus.UNAUTHORIZED,
                error_message=str(e),
                last_updated=now,
            )
        except (SQLCompilationError, SQLValidationError, Exception) as e:
            logger.error(f"Widget {widget.widget_id} compilation error: {e}")
            return DashboardWidgetResult(
                widget_id=widget.widget_id,
                metric_id=widget.metric_id,
                metric_display_name=display_name,
                title=widget.title,
                visualization_type=widget.visualization_type.value,
                status=WidgetStatus.ERROR,
                error_message="Analytical query compilation error.",
                last_updated=now,
            )

        # Step 4: Execute against Read-Only Database
        try:
            query_result = self._executor.execute_artifact(
                artifact=validated_artifact,
                principal=principal,
            )
        except DatabaseNotConfiguredError:
            return DashboardWidgetResult(
                widget_id=widget.widget_id,
                metric_id=widget.metric_id,
                metric_display_name=display_name,
                title=widget.title,
                visualization_type=widget.visualization_type.value,
                status=WidgetStatus.UNAVAILABLE,
                error_message="Institutional database is not currently configured.",
                last_updated=now,
            )
        except Exception as e:
            logger.error(f"Widget {widget.widget_id} execution error: {e}")
            return DashboardWidgetResult(
                widget_id=widget.widget_id,
                metric_id=widget.metric_id,
                metric_display_name=display_name,
                title=widget.title,
                visualization_type=widget.visualization_type.value,
                status=WidgetStatus.ERROR,
                error_message="Query execution error against institutional database.",
                last_updated=now,
            )

        # Step 5: Deterministic Visualization & Explanation
        intent_dict = intent.model_dump()
        viz = self._visualizer.select_visualization(
            query_result=query_result,
            intent=intent_dict,
            metric_id=widget.metric_id,
        )
        explanation = self._visualizer.generate_explanation(
            query_result=query_result,
            intent=intent_dict,
            metric_id=widget.metric_id,
        )

        # Step 6: Deterministic Anomaly Assessment
        anomaly_assessment = None
        if settings.ANOMALY_DETECTION_ENABLED:
            try:
                anomaly_assessment = self._anomaly_detector.assess_result(
                    query_result=query_result,
                    intent=intent_dict,
                    metric_id=widget.metric_id,
                )
            except Exception as e:
                logger.warning(f"Widget {widget.widget_id} anomaly assessment skipped: {e}")

        status = (
            WidgetStatus.EMPTY
            if query_result.status == QueryResultStatus.EMPTY
            else (
                WidgetStatus.SUCCESS
                if query_result.status == QueryResultStatus.SUCCESS
                else WidgetStatus.ERROR
            )
        )

        return DashboardWidgetResult(
            widget_id=widget.widget_id,
            metric_id=widget.metric_id,
            metric_display_name=display_name,
            title=widget.title,
            visualization_type=widget.visualization_type.value,
            visualization=viz,
            result=query_result,
            anomaly=anomaly_assessment,
            explanation=explanation,
            status=status,
            last_updated=now,
        )


_singleton_dashboard_service: Optional[DashboardService] = None


def get_dashboard_service() -> DashboardService:
    """Dependency injection provider for DashboardService."""
    global _singleton_dashboard_service
    if _singleton_dashboard_service is None:
        _singleton_dashboard_service = DashboardService()
    return _singleton_dashboard_service
