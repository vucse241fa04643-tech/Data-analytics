"""Agent 63 - Phase 9: Visualization Schema
Deterministic visualization descriptor schema for institutional analytics presentation.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ChartType(str, Enum):
    """Deterministic chart presentation types."""
    KPI = "kpi"
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    LINE = "line"
    TABLE = "table"
    NONE = "none"


class VisualizationDescriptor(BaseModel):
    """Deterministic visualization specification derived strictly from validated QueryResult and Semantic Layer."""
    recommended: bool = Field(
        ...,
        description="Whether a graphic visualization (KPI, bar, horizontal_bar, line) is recommended over default table",
    )
    chart_type: ChartType = Field(
        ...,
        description="Selected visualization format (kpi, bar, horizontal_bar, line, table, none)",
    )
    x_field: Optional[str] = Field(
        default=None,
        description="Dimension field name for X-axis / category axis",
    )
    y_field: Optional[str] = Field(
        default=None,
        description="Metric field name for Y-axis / value axis",
    )
    title: Optional[str] = Field(
        default=None,
        description="Institutional title for the visualization",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Metric unit (e.g. '%', 'students', 'marks') from the authoritative semantic registry",
    )
    description: Optional[str] = Field(
        default=None,
        description="Semantic context or note explaining the visual representation",
    )
