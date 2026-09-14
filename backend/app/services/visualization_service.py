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
    if u in ("count", "integer", "number", "none", "kpi_unit"):
        return ""
    if u in ("students", "students_count"):
        return " students"
    if u == "offerings_count":
        return " course offerings"
    if u == "marks":
        return " marks"
    if u == "credits":
        return " credits"
    if u == "cgpa":
        return " CGPA"
    if u in ("inr_lakhs_per_annum", "lpa"):
        return " lakh/year"
    if u in ("level_scale", "scale_1_to_3"):
        return ""
    if u == "score_0_to_100":
        return "/100"
    return f" {unit}"


def _format_value_with_unit(value: Any, unit_sym: str) -> str:
    """Formats numeric or string value with appropriate human-readable unit placement."""
    if value is None:
        return "N/A"
    u_sym = unit_sym.strip().lower() if unit_sym else ""
    if "lakh/year" in u_sym or "inr" in u_sym or "lpa" in u_sym:
        try:
            num = float(value)
            if num >= 1000.0:
                lakhs = num / 100000.0
                return f"₹{lakhs:.2f} lakh/year"
            return f"₹{num:.2f} lakh/year"
        except (ValueError, TypeError):
            return f"₹{value} lakh/year"

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
            is_self = False
            if intent and isinstance(intent, dict):
                raw_filters = intent.get("filters") or intent.get("student_filters") or {}
                if raw_filters.get("student_id") == "SELF":
                    is_self = True

            kpi_desc = (
                f"Personal self-scoped attendance KPI for {display_name}."
                if is_self
                else f"Single-value institutional KPI for {display_name}."
            )
            return VisualizationDescriptor(
                recommended=True,
                chart_type=ChartType.KPI,
                x_field=None,
                y_field=val_col,
                title=display_name,
                unit=raw_unit,
                description=kpi_desc,
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

            is_comparison = False
            comparison_label = ""
            if intent and isinstance(intent, dict):
                i_type = intent.get("intent_type")
                r_filters = intent.get("filters") or {}
                dept_val = r_filters.get("department")

                if i_type == "BASELINE_COMPARISON":
                    op = intent.get("operator") or ("<" if any(w in (intent.get("reasoning_summary") or "").lower() for w in ["below", "lower", "under"]) else ">")
                    direction_word = "Below" if op == "<" else "Above"
                    clean_m = "Attendance" if "attendance" in (m_id or "").lower() else display_name
                    is_dept_base = intent.get("baseline") == "DEPARTMENT"
                    base_label = "Department" if is_dept_base else "Institutional"
                    dim_entity = "Departments" if dim_col == "department" else (dim_col.replace("_", " ").title() + "s" if not dim_col.endswith("s") else dim_col.replace("_", " ").title())
                    v_title = f"{dim_entity} {direction_word} {base_label} {clean_m}"
                    v_desc = f"{base_label} baseline comparison of {display_name} for qualifying {dim_entity.lower()}."
                    return VisualizationDescriptor(
                        recommended=True,
                        chart_type=ChartType.BAR,
                        x_field=dim_col,
                        y_field=val_col,
                        title=v_title,
                        unit=raw_unit,
                        description=v_desc,
                    )

                if i_type == "THRESHOLD_QUERY":
                    th = intent.get("threshold") or (intent.get("filters") or {}).get("threshold")
                    op = intent.get("operator") or ("<" if any(w in (intent.get("reasoning_summary") or "").lower() for w in ["below", "lower", "under"]) else ">")
                    clean_m = "Attendance" if "attendance" in (m_id or "").lower() else display_name
                    th_str = f" ({op} {th}{unit_sym})" if th is not None else ""
                    dim_entity = "Departments" if dim_col == "department" else (dim_col.replace("_", " ").title() + "s" if not dim_col.endswith("s") else dim_col.replace("_", " ").title())
                    v_title = f"{dim_entity} with {clean_m}{th_str}"
                    v_desc = f"Threshold analysis of {display_name} across qualifying {dim_entity.lower()}."
                    return VisualizationDescriptor(
                        recommended=True,
                        chart_type=ChartType.BAR,
                        x_field=dim_col,
                        y_field=val_col,
                        title=v_title,
                        unit=raw_unit,
                        description=v_desc,
                    )

                if i_type == "RANKING_QUERY":
                    u_order = intent.get("order") or (intent.get("filters") or {}).get("order")
                    u_limit = intent.get("limit") or (intent.get("filters") or {}).get("limit")
                    is_lowest = str(u_order or "").lower() in ("asc", "lowest", "bottom")
                    clean_m = "Attendance" if "attendance" in (m_id or "").lower() else display_name
                    dim_entity = "Departments" if dim_col == "department" else (dim_col.replace("_", " ").title() + "s" if not dim_col.endswith("s") else dim_col.replace("_", " ").title())
                    dim_entity_sing = "Department" if dim_col == "department" else dim_col.replace("_", " ").title()
                    if u_limit and int(u_limit) == 1 and query_result.row_count == 1:
                        dim_val = str(query_result.rows[0].get(dim_col, ""))
                        rank_word = "Lowest" if is_lowest else "Highest"
                        return VisualizationDescriptor(
                            recommended=True,
                            chart_type=ChartType.KPI,
                            x_field=dim_col,
                            y_field=val_col,
                            title=f"{rank_word} {clean_m} ({dim_val})",
                            unit=raw_unit,
                            description=f"{dim_entity_sing} with the {rank_word.lower()} {clean_m.lower()}.",
                        )
                    elif u_limit:
                        rank_word = "Bottom" if is_lowest else "Top"
                        v_title = f"{rank_word} {u_limit} {dim_entity} by {clean_m}"
                        v_desc = f"Ranked {dim_entity.lower()} by {display_name}."
                        return VisualizationDescriptor(
                            recommended=True,
                            chart_type=ChartType.BAR,
                            x_field=dim_col,
                            y_field=val_col,
                            title=v_title,
                            unit=raw_unit,
                            description=v_desc,
                        )

                if i_type == "TREND_QUERY":
                    clean_m = "Attendance" if "attendance" in (m_id or "").lower() else display_name
                    return VisualizationDescriptor(
                        recommended=True,
                        chart_type=ChartType.LINE,
                        x_field=dim_col,
                        y_field=val_col,
                        title=f"{clean_m} Trend by Academic Year",
                        unit=raw_unit,
                        description=f"Chronological trend of {display_name} by academic year.",
                    )

                if i_type == "COMPARISON_QUERY" or (isinstance(dept_val, list) and len(dept_val) >= 2):
                    is_comparison = True
                    if isinstance(dept_val, list) and len(dept_val) >= 2:
                        comparison_label = " vs ".join(str(d) for d in dept_val)
                    else:
                        comparison_label = " vs ".join(sample_labels)

            v_title = (
                f"{display_name} ({comparison_label})"
                if is_comparison
                else f"{display_name} by {dim_col.replace('_', ' ').title()}"
            )
            v_desc = (
                f"Comparative analysis of {display_name} between {comparison_label}."
                if is_comparison
                else f"Categorical comparison of {display_name} across {dim_col.replace('_', ' ')}."
            )

            return VisualizationDescriptor(
                recommended=True,
                chart_type=ChartType.HORIZONTAL_BAR if use_horizontal else ChartType.BAR,
                x_field=dim_col,
                y_field=val_col,
                title=v_title,
                unit=raw_unit,
                description=v_desc,
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

        # Specialized analytical operations explanations
        if intent and isinstance(intent, dict):
            i_type = intent.get("intent_type")
            if i_type == "BASELINE_COMPARISON":
                dim_k = dimension_cols[0] if dimension_cols else "department"
                dim_entity = "departments" if dim_k == "department" else (dim_k.replace("_", " ") + "s" if not dim_k.endswith("s") else dim_k.replace("_", " "))
                is_dept_base = intent.get("baseline") == "DEPARTMENT"
                base_type_label = "department" if is_dept_base else "institutional"
                if query_result.rows:
                    first_r = query_result.rows[0]
                    dim_v = str(first_r.get(dim_k, ""))
                    m_val = first_r.get("metric_value")
                    b_val = first_r.get("baseline_value")
                    diff_val = first_r.get("difference")
                    clean_m = "attendance" if "attendance" in (m_id or "").lower() else display_name.lower()
                    op = intent.get("operator") or ("<" if any(w in (intent.get("reasoning_summary") or "").lower() for w in ["below", "lower", "under"]) else ">")
                    dir_word = "below" if op == "<" or (diff_val is not None and float(diff_val) < 0) else "above"
                    diff_str = f"{float(diff_val):.2f}" if diff_val is not None else "0.00"
                    pts_label = "percentage points" if unit_sym == "%" else unit_sym
                    return (
                        f"{dim_v} is {dir_word} the {base_type_label} {clean_m} level. {dim_v} {clean_m} is {_format_value_with_unit(m_val, unit_sym)}, "
                        f"compared with a {base_type_label} baseline of {_format_value_with_unit(b_val, unit_sym)}, a difference of {diff_str} {pts_label}."
                    )
                else:
                    return f"No {dim_entity} were found satisfying the requested baseline comparison criteria."

            if i_type == "RANKING_QUERY":
                u_order = intent.get("order") or (intent.get("filters") or {}).get("order")
                u_limit = intent.get("limit") or (intent.get("filters") or {}).get("limit")
                is_lowest = str(u_order or "").lower() in ("asc", "lowest", "bottom")
                clean_m = "attendance" if "attendance" in (m_id or "").lower() else display_name.lower()
                dim_k = dimension_cols[0] if dimension_cols else "department"
                dim_entity = "departments" if dim_k == "department" else (dim_k.replace("_", " ") + "s" if not dim_k.endswith("s") else dim_k.replace("_", " "))
                if (u_limit and int(u_limit) == 1) or query_result.row_count == 1:
                    first_r = query_result.rows[0]
                    dim_v = str(first_r.get(dim_k, ""))
                    m_val = first_r.get("metric_value") or (first_r.get(numeric_cols[0]) if numeric_cols else None)
                    rank_word = "lowest" if is_lowest else "highest"
                    return f"{dim_v} has the {rank_word} current {clean_m} among the returned {dim_entity} at {_format_value_with_unit(m_val, unit_sym)}."

            if i_type == "TREND_QUERY":
                if not query_result.rows or len(query_result.rows) < 2:
                    return "Insufficient historical data is available for this analysis."
                first_r = query_result.rows[0]
                last_r = query_result.rows[-1]
                dim_k = dimension_cols[0] if dimension_cols else "academic_year"
                first_t = first_r.get(dim_k)
                last_t = last_r.get(dim_k)
                first_v = _format_value_with_unit(first_r.get("metric_value"), unit_sym)
                last_v = _format_value_with_unit(last_r.get("metric_value"), unit_sym)
                return (
                    f"{display_name} trend across {len(query_result.rows)} academic periods spans from "
                    f"{first_v} ({first_t}) to {last_v} ({last_t})."
                )

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

                is_comp = False
                if intent and isinstance(intent, dict):
                    i_type = intent.get("intent_type")
                    dept_val = (intent.get("filters") or {}).get("department")
                    if i_type == "COMPARISON_QUERY" or (isinstance(dept_val, list) and len(dept_val) >= 2):
                        is_comp = True

                if is_comp and len(valid_rows) == 2:
                    return (
                        f"{display_name} comparison: {max_dim} is {max_val} compared to {min_dim} at {min_val}."
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
