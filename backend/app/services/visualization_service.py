"""Agent 63 - Phase 9: Visualization Service
Deterministic visualization selection and deterministic analytical explanation generation.

Authoritative Rules:
- RULE A: 1 numeric metric with 1 result row -> KPI
- RULE B: 1 categorical dimension + 1 numeric metric -> Bar or Horizontal Bar
- RULE C: Time/date dimension + numeric metric -> Line chart
- RULE D: Multiple dimensions or ambiguous semantics -> Table
- RULE E: Unsupported result shape or empty results -> Table or None

No external LLM / Groq calls are used. All explanations and chart decisions are 100% deterministic,
semantically grounded in Phase 4 metadata and Phase 8 validated QueryResults.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.logging import get_logger
from backend.app.schemas.query_result import QueryResult, QueryResultStatus
from backend.app.schemas.visualization import ChartType, VisualizationDescriptor
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)

logger = get_logger("agent63.services.visualization")

TEMPORAL_DIMENSIONS = {
    "dim.academic_year",
    "dim.term",
    "academic_year",
    "term",
    "year",
    "date",
    "month",
    "semester",
    "admission_year",
    "graduation_year",
    "assessment_date",
    "attendance_date",
}


def _format_unit_symbol(unit: Optional[str]) -> str:
    """Normalizes unit strings into clean concise presentation symbols."""
    if not unit:
        return ""
    u = unit.strip().lower()
    if u in ("percentage", "percent", "%"):
        return "%"
    if u in ("count", "integer", "number", "none"):
        return ""
    if u == "students":
        return " students"
    if u == "marks":
        return " marks"
    if u == "credits":
        return " credits"
    if u == "cgpa":
        return " CGPA"
    if u == "lpa":
        return " LPA"
    return f" {unit}"


def _format_value_with_unit(value: Any, unit_sym: str) -> str:
    """Formats numeric or string value with appropriate unit placement."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        formatted = str(value)
    if unit_sym.startswith("%"):
        return f"{formatted}{unit_sym}"
    return f"{formatted}{unit_sym}"


class VisualizationService:
    """Deterministic visualization recommendation and explanation service."""

    def __init__(self, semantic_registry: Optional[SemanticRegistryService] = None):
        self._semantic = semantic_registry or get_semantic_registry_service()

    def _get_metric_meta(self, metric_id: Optional[str]) -> Tuple[str, str, Optional[str]]:
        """Extracts display name, unit symbol, and description from semantic registry.
        
        Returns: (display_name, unit_symbol, raw_unit)
        """
        if not metric_id:
            return "Institutional Metric", "", None
        metric_def = self._semantic.get_metric(metric_id)
        if not metric_def:
            # Fall back to title-cased canonical identifier
            name_part = metric_id.split(".")[-1].replace("_", " ").title()
            return name_part, "", None
        display_name = metric_def.get("display_name") or metric_id
        raw_unit = metric_def.get("unit")
        unit_sym = _format_unit_symbol(raw_unit)
        return display_name, unit_sym, raw_unit

    def _classify_columns(
        self,
        columns: List[str],
        data_types: Dict[str, str],
        rows: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[str]]:
        """Classifies columns into numeric metrics and dimensions based on metadata and values."""
        numeric_cols: List[str] = []
        dimension_cols: List[str] = []

        numeric_types = {"numeric", "integer", "float", "double", "bigint", "real", "decimal"}

        for col in columns:
            dtype = data_types.get(col, "").lower()
            if any(nt in dtype for nt in numeric_types):
                numeric_cols.append(col)
            elif dtype in ("character varying", "text", "varchar", "char", "name"):
                dimension_cols.append(col)
            else:
                # Inspect sample values from rows
                sample_vals = [r[col] for r in rows if r.get(col) is not None][:10]
                if sample_vals and all(isinstance(v, (int, float)) for v in sample_vals):
                    numeric_cols.append(col)
                else:
                    dimension_cols.append(col)

        return numeric_cols, dimension_cols

    def _is_temporal_column(self, col_name: str, metric_id: Optional[str]) -> bool:
        """Checks whether a column represents a time or date dimension."""
        c = col_name.lower()
        if c in TEMPORAL_DIMENSIONS or any(t in c for t in ("year", "date", "term", "month", "semester")):
            return True
        if metric_id:
            metric_def = self._semantic.get_metric(metric_id)
            if metric_def:
                time_sem = metric_def.get("time_semantics", {})
                time_col = time_sem.get("time_column")
                time_dim = time_sem.get("time_dimension")
                if time_col and c == time_col.lower():
                    return True
                if time_dim and (c == time_dim.lower() or time_dim.lower().endswith(c)):
                    return True
        return False

    def select_visualization(
        self,
        query_result: QueryResult,
        intent: Optional[Dict[str, Any]] = None,
        metric_id: Optional[str] = None,
    ) -> VisualizationDescriptor:
        """Deterministically selects chart type according to Rules A-E."""
        m_id = metric_id or (query_result.metadata.metric_id if query_result.metadata else None)
        display_name, unit_sym, raw_unit = self._get_metric_meta(m_id)

        # RULE E: Empty result or execution failure
        if query_result.status != QueryResultStatus.SUCCESS or query_result.row_count == 0 or not query_result.rows:
            return VisualizationDescriptor(
                recommended=False,
                chart_type=ChartType.NONE,
                x_field=None,
                y_field=None,
                title=f"{display_name} (No Data)",
                unit=raw_unit,
                description="No records available for visualization.",
            )

        columns = query_result.columns
        data_types = query_result.metadata.data_types if query_result.metadata else {}
        numeric_cols, dimension_cols = self._classify_columns(columns, data_types, query_result.rows)

        # RULE A: 1 numeric metric with 1 result row -> KPI
        if query_result.row_count == 1 and len(numeric_cols) >= 1 and len(dimension_cols) == 0:
            val_col = numeric_cols[0]
            return VisualizationDescriptor(
                recommended=True,
                chart_type=ChartType.KPI,
                x_field=None,
                y_field=val_col,
                title=display_name,
                unit=raw_unit,
                description=f"Single-value institutional KPI for {display_name}.",
            )

        # Also Rule A edge case: 1 row with 1 dimension and 1 numeric (e.g. filtered to CSE only)
        if query_result.row_count == 1 and len(numeric_cols) == 1 and len(dimension_cols) == 1:
            dim_col = dimension_cols[0]
            val_col = numeric_cols[0]
            dim_val = str(query_result.rows[0].get(dim_col, ""))
            return VisualizationDescriptor(
                recommended=True,
                chart_type=ChartType.KPI,
                x_field=dim_col,
                y_field=val_col,
                title=f"{display_name} ({dim_val})",
                unit=raw_unit,
                description=f"Single-scope KPI for {dim_val}.",
            )

        # Multi-row cases
        if len(numeric_cols) == 1 and len(dimension_cols) == 1:
            dim_col = dimension_cols[0]
            val_col = numeric_cols[0]

            # RULE C: Time/date dimension + numeric metric -> Line chart
            if self._is_temporal_column(dim_col, m_id):
                return VisualizationDescriptor(
                    recommended=True,
                    chart_type=ChartType.LINE,
                    x_field=dim_col,
                    y_field=val_col,
                    title=f"{display_name} Over Time",
                    unit=raw_unit,
                    description=f"Chronological trend of {display_name} by {dim_col}.",
                )

            # RULE B: Categorical dimension + numeric metric -> Bar or Horizontal Bar
            # Heuristic: Use horizontal bar if labels are long (>12 chars avg) or >= 6 rows
            sample_labels = [str(r.get(dim_col, "")) for r in query_result.rows]
            avg_len = sum(len(l) for l in sample_labels) / max(len(sample_labels), 1)
            use_horizontal = avg_len > 12 or len(sample_labels) > 6

            return VisualizationDescriptor(
                recommended=True,
                chart_type=ChartType.HORIZONTAL_BAR if use_horizontal else ChartType.BAR,
                x_field=dim_col,
                y_field=val_col,
                title=f"{display_name} by {dim_col.replace('_', ' ').title()}",
                unit=raw_unit,
                description=f"Categorical comparison of {display_name} across {dim_col.replace('_', ' ')}.",
            )

        # RULE D: Multiple dimensions or ambiguous semantics -> Table
        return VisualizationDescriptor(
            recommended=False,
            chart_type=ChartType.TABLE,
            x_field=dimension_cols[0] if dimension_cols else (columns[0] if columns else None),
            y_field=numeric_cols[0] if numeric_cols else None,
            title=f"{display_name} Tabular View",
            unit=raw_unit,
            description="Multi-dimensional dataset best viewed in tabular format.",
        )

    def generate_explanation(
        self,
        query_result: QueryResult,
        intent: Optional[Dict[str, Any]] = None,
        metric_id: Optional[str] = None,
    ) -> str:
        """Deterministically synthesizes an analytical narrative summary without LLM calls."""
        m_id = metric_id or (query_result.metadata.metric_id if query_result.metadata else None)
        display_name, unit_sym, _ = self._get_metric_meta(m_id)

        # Edge cases: Error or Empty
        if query_result.status == QueryResultStatus.ERROR or query_result.error:
            return "Agent 63 could not complete the query safely. Please verify filters and institutional scope."
        if query_result.status == QueryResultStatus.EMPTY or query_result.row_count == 0 or not query_result.rows:
            return "No matching institutional records were found for the specified criteria."
        if query_result.status == QueryResultStatus.DATABASE_NOT_CONFIGURED:
            return "College database is currently unavailable."

        columns = query_result.columns
        data_types = query_result.metadata.data_types if query_result.metadata else {}
        numeric_cols, dimension_cols = self._classify_columns(columns, data_types, query_result.rows)

        # Scope context from intent filters if available
        scope_clauses = []
        if intent and isinstance(intent, dict):
            filters = intent.get("filters", {})
            for k, v in filters.items():
                if v is not None and k not in ("is_active", "status"):
                    clean_k = k.replace("_id", "").replace("_code", "").replace("_", " ").title()
                    scope_clauses.append(f"{clean_k}: {v}")
        scope_str = f" ({', '.join(scope_clauses)})" if scope_clauses else ""

        # Case 1: Exactly 1 row, 1 numeric value (Rule A single KPI)
        if query_result.row_count == 1:
            row = query_result.rows[0]
            if numeric_cols:
                val = row[numeric_cols[0]]
                val_str = _format_value_with_unit(val, unit_sym)
                if dimension_cols:
                    dim_val = row[dimension_cols[0]]
                    return f"The {display_name} for {dim_val}{scope_str} is {val_str}."
                return f"The {display_name}{scope_str} is {val_str}."
            # Non-numeric 1 row
            items_str = ", ".join(f"{k}: {v}" for k, v in row.items())
            return f"Institutional record for {display_name}: {items_str}."

        # Case 2: Multi-row with 1 numeric metric and 1 dimension (Rule B & C)
        if len(numeric_cols) >= 1 and len(dimension_cols) >= 1:
            val_col = numeric_cols[0]
            dim_col = dimension_cols[0]

            valid_rows = [r for r in query_result.rows if r.get(val_col) is not None]
            if not valid_rows:
                return f"All {query_result.row_count} records returned NULL values for {display_name}."

            # Temporal line narrative
            if self._is_temporal_column(dim_col, m_id):
                first_row = valid_rows[0]
                last_row = valid_rows[-1]
                first_t = first_row.get(dim_col)
                last_t = last_row.get(dim_col)
                first_v = _format_value_with_unit(first_row.get(val_col), unit_sym)
                last_v = _format_value_with_unit(last_row.get(val_col), unit_sym)
                return (
                    f"{display_name} across {len(valid_rows)} periods spans from "
                    f"{first_v} ({first_t}) to {last_v} ({last_t})."
                )

            # Categorical comparison narrative
            # Find min and max
            try:
                sorted_rows = sorted(valid_rows, key=lambda r: float(r[val_col]))
                min_row = sorted_rows[0]
                max_row = sorted_rows[-1]
                min_val = _format_value_with_unit(min_row[val_col], unit_sym)
                max_val = _format_value_with_unit(max_row[val_col], unit_sym)
                min_dim = min_row.get(dim_col)
                max_dim = max_row.get(dim_col)

                if min_dim == max_dim or min_row[val_col] == max_row[val_col]:
                    return (
                        f"All {len(valid_rows)} reported {dim_col.replace('_', ' ')} categories have "
                        f"a {display_name} of {max_val}."
                    )

                return (
                    f"{display_name} is highest for {max_dim} at {max_val} and lowest for {min_dim} at {min_val} "
                    f"across {len(valid_rows)} reported {dim_col.replace('_', ' ')} categories."
                )
            except (ValueError, TypeError):
                return (
                    f"Returned {len(valid_rows)} {dim_col.replace('_', ' ')} records for {display_name}."
                )

        # Case 3: General multi-row or multi-dimensional table
        return (
            f"Returned {query_result.row_count} validated institutional records for {display_name}."
        )


_visualization_service: Optional[VisualizationService] = None


def get_visualization_service() -> VisualizationService:
    """Returns singleton instance of VisualizationService."""
    global _visualization_service
    if _visualization_service is None:
        _visualization_service = VisualizationService()
    return _visualization_service
