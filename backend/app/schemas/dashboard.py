"""Agent 63 - Phase 12: Role-Based Institutional Dashboard Schemas
Pydantic domain models and API contracts for role-specific analytics dashboards,
widget specifications, deterministic execution results, and scheduled refresh configurations.

CRITICAL ARCHITECTURAL CONSTRAINTS:
- Dashboard visibility is presentation only; backend authorization remains authoritative.
- Never allows raw SQL in widget or dashboard definitions.
- Widgets reference ONLY approved semantic catalog metrics.
- Enforces multi-tier defense-in-depth: RBAC, scope predicates, AST validation, read-only DB.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.anomaly import AnomalyAssessment
from backend.app.schemas.query_result import QueryResult
from backend.app.schemas.visualization import VisualizationDescriptor


class WidgetVisualizationType(str, Enum):
    """Deterministic visual presentation formats for dashboard widgets."""
    KPI = "KPI"
    BAR_CHART = "BAR_CHART"
    LINE_CHART = "LINE_CHART"
    TABLE = "TABLE"


class WidgetRefreshPolicy(str, Enum):
    """Configured widget refresh frequency policy."""
    INHERIT = "INHERIT"
    MANUAL = "MANUAL"
    HOURLY = "HOURLY"
    DAILY = "DAILY"


class WidgetStatus(str, Enum):
    """Execution status of an individual dashboard widget."""
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"


class WidgetDefinition(BaseModel):
    """Server-side specification for a dashboard analytical widget."""
    widget_id: str = Field(..., description="Unique immutable identifier for this widget")
    metric_id: str = Field(..., description="Approved semantic catalog metric ID")
    title: str = Field(..., description="Human-readable institutional title for the widget")
    description: Optional[str] = Field(None, description="Contextual analytical guidance")
    visualization_type: WidgetVisualizationType = Field(
        default=WidgetVisualizationType.KPI,
        description="Target visual card representation"
    )
    dimension: Optional[str] = Field(
        None,
        description="Optional semantic dimension for breakdown (e.g., dim.department)"
    )
    default_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-configured semantic filters (never overrides user scope)"
    )
    refresh_policy: WidgetRefreshPolicy = Field(
        default=WidgetRefreshPolicy.INHERIT,
        description="Refresh cadence policy"
    )
    display_order: int = Field(default=0, description="Display sort ordering")


class DashboardDefinition(BaseModel):
    """Server-controlled institutional dashboard layout and metric definition."""
    dashboard_id: str = Field(..., description="Unique dashboard identifier (e.g., principal_executive)")
    title: str = Field(..., description="Institutional dashboard display name")
    description: str = Field(..., description="Role and scope purpose description")
    allowed_roles: List[str] = Field(..., description="Institutional roles permitted to access this dashboard")
    default_role: str = Field(..., description="Primary institutional role intended for this view")
    widgets: List[WidgetDefinition] = Field(default_factory=list, description="Ordered widget specifications")


class DashboardCatalogItem(BaseModel):
    """Brief metadata entry representing an available dashboard for the user."""
    dashboard_id: str
    title: str
    description: str
    role: str
    widget_count: int
    is_default: bool = False


class DashboardCatalogResponse(BaseModel):
    """List of all dashboards authorized for the current authenticated principal."""
    dashboards: List[DashboardCatalogItem] = Field(default_factory=list)
    user_roles: List[str] = Field(default_factory=list)
    active_dashboard_id: Optional[str] = None


class DashboardWidgetResult(BaseModel):
    """Execution output and analytical presentation for an individual widget."""
    widget_id: str
    metric_id: str
    metric_display_name: str
    title: str
    visualization_type: str
    visualization: Optional[VisualizationDescriptor] = None
    result: Optional[QueryResult] = None
    anomaly: Optional[AnomalyAssessment] = None
    explanation: Optional[str] = None
    status: WidgetStatus = WidgetStatus.SUCCESS
    error_message: Optional[str] = None
    last_updated: datetime


class DashboardResponse(BaseModel):
    """Full role-based institutional dashboard response payload."""
    dashboard_id: str
    title: str
    description: Optional[str] = None
    role: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    last_refreshed_at: datetime
    refresh_mode: str = Field(default="MANUAL", description="MANUAL | SCHEDULED | CACHED")
    refresh_status: str = Field(default="COMPLETED", description="COMPLETED | PARTIAL_FAILURE | FAILED")
    widgets: List[DashboardWidgetResult] = Field(default_factory=list)


class DashboardScheduleRequest(BaseModel):
    """Request payload to configure or update a scheduled dashboard refresh."""
    dashboard_id: str = Field(..., description="Target dashboard identifier to schedule")
    interval_minutes: int = Field(
        default=60,
        ge=60,
        description="Refresh interval in minutes (minimum 60 minutes enforced)"
    )


class DashboardScheduleItem(BaseModel):
    """Active scheduled dashboard refresh job metadata."""
    schedule_id: str
    dashboard_id: str
    dashboard_title: str
    user_id: str
    role: str
    interval_minutes: int
    created_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    is_active: bool = True
    last_status: Optional[str] = None
