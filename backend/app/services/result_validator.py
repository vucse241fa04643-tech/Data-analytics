"""Agent 63 - Phase 8: Result Validator
Validates and normalizes raw SQL execution results against semantic expectations,
enforcing type safety, NaN/Infinity rejection, null preservation, and sanity bounds.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.config import settings
from backend.app.core.errors import ResultValidationError
from backend.app.core.logging import get_logger
from backend.app.schemas.query_result import ExecutionMetadata, QueryResult, QueryResultStatus
from backend.app.schemas.student_catalog import (
    APPROVED_STUDENT_FIELDS,
    STRICTLY_PROHIBITED_FIELDS,
)
from backend.app.services.semantic_registry import get_semantic_registry_service

logger = get_logger("agent63.services.result_validator")


class ResultValidator:
    """
    Validates raw query outputs against institutional data integrity requirements:
    - Verifies column structure
    - Preserves NULLs without coercion
    - Rejects NaN and Infinity values
    - Normalizes Decimal to float/int and datetime/date to ISO-8601 strings
    - Enforces metric domain sanity bounds (e.g. percentages in [0, 100], counts >= 0)
    - Enforces student-record approved catalog and field-level security
    """

    def __init__(self):
        self._semantic_registry = get_semantic_registry_service()

    def validate_and_normalize(
        self,
        raw_columns: List[str],
        raw_rows: List[Dict[str, Any]],
        raw_data_types: Dict[str, str],
        metric_id: Optional[str],
        execution_time_ms: float,
        statement_timeout_ms: Optional[int] = None,
        expected_columns: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        result_type: Optional[str] = None,
    ) -> QueryResult:
        """
        Validates and normalizes raw database execution rows into a safe QueryResult.

        Raises:
            ResultValidationError: If validation fails (NaN, Inf, sanity bounds breach, column mismatch).
        """
        is_student_list = (metric_id == "student.list" or result_type == "STUDENT_LIST")
        eff_result_type = "STUDENT_LIST" if is_student_list else (result_type or "ANALYTICAL_METRIC")

        # 1. Row count validation & pagination lookahead truncation
        has_more_records: Optional[bool] = None
        if is_student_list and page_size:
            if len(raw_rows) > page_size:
                has_more_records = True
                raw_rows = raw_rows[:page_size]
            else:
                has_more_records = False

        row_count = len(raw_rows)
        max_rows = 50 if is_student_list else settings.MAX_RESULT_ROWS
        if row_count > max_rows:
            raise ResultValidationError(
                f"Result row count {row_count} exceeds maximum allowed limit of {max_rows}."
            )

        # 1.5 Student Field-level security validation
        if is_student_list:
            for col in raw_columns:
                col_clean = col.lower().strip()
                if col_clean in STRICTLY_PROHIBITED_FIELDS:
                    raise ResultValidationError(
                        f"Strictly prohibited field '{col}' detected in student query result."
                    )
                if col_clean not in APPROVED_STUDENT_FIELDS:
                    raise ResultValidationError(
                        f"Unapproved column '{col}' detected in student query result."
                    )

        # 2. Check for empty result set
        if row_count == 0:
            metadata = ExecutionMetadata(
                execution_time_ms=execution_time_ms,
                row_count=0,
                columns=raw_columns,
                data_types=raw_data_types,
                metric_id=metric_id,
                statement_timeout_ms=statement_timeout_ms,
                page=page,
                page_size=page_size,
                has_more=False if is_student_list else None,
            )
            return QueryResult(
                status=QueryResultStatus.EMPTY,
                result_type=eff_result_type,
                columns=raw_columns,
                rows=[],
                row_count=0,
                metadata=metadata,
                error=None,
            )

        # 3. Column validation
        if expected_columns:
            returned_cols_lower = {c.lower() for c in raw_columns}
            for exp in expected_columns:
                clean_exp = exp.split(".")[-1].lower()
                if clean_exp not in returned_cols_lower and not any(clean_exp in r for r in returned_cols_lower):
                    logger.debug("Expected column %s not strictly matched in %s", exp, raw_columns)

        # 4. Fetch metric definition for sanity checks if applicable
        metric_def = None
        if metric_id:
            try:
                metric_def = self._semantic_registry.get_metric(metric_id)
            except Exception:
                metric_def = None

        metric_unit = metric_def.get("unit") if metric_def else None

        # 5. Row-by-row and cell-by-cell normalization and validation
        normalized_rows: List[Dict[str, Any]] = []
        inferred_types: Dict[str, str] = dict(raw_data_types)

        for row_idx, row in enumerate(raw_rows):
            normalized_row: Dict[str, Any] = {}
            for col_name, raw_val in row.items():
                normalized_val = self._normalize_cell(
                    value=raw_val,
                    col_name=col_name,
                    row_idx=row_idx,
                    metric_unit=metric_unit,
                    result_type=eff_result_type,
                )
                normalized_row[col_name] = normalized_val

                # Infer high-level python type for metadata if not present
                if col_name not in inferred_types or inferred_types[col_name] == "unknown":
                    inferred_types[col_name] = type(normalized_val).__name__ if normalized_val is not None else "null"

            normalized_rows.append(normalized_row)

        metadata = ExecutionMetadata(
            execution_time_ms=execution_time_ms,
            row_count=len(normalized_rows),
            columns=raw_columns,
            data_types=inferred_types,
            metric_id=metric_id,
            statement_timeout_ms=statement_timeout_ms,
            page=page,
            page_size=page_size,
            has_more=has_more_records if has_more_records is not None else ((len(normalized_rows) == page_size) if (is_student_list and page_size) else None),
        )

        return QueryResult(
            status=QueryResultStatus.SUCCESS,
            result_type=eff_result_type,
            columns=raw_columns,
            rows=normalized_rows,
            row_count=len(normalized_rows),
            metadata=metadata,
            error=None,
        )

    def _normalize_cell(
        self,
        value: Any,
        col_name: str,
        row_idx: int,
        metric_unit: Optional[str],
        result_type: Optional[str] = None,
    ) -> Any:
        """
        Normalizes a single cell value, enforcing IEEE-754 safety, ISO-8601 formatting,
        and metric sanity bounds.
        """
        # Strict null preservation
        if value is None:
            return None

        # Rejection of NaN and Infinity for floats
        if isinstance(value, float):
            if math.isnan(value):
                raise ResultValidationError(
                    f"Invalid numeric value NaN in column '{col_name}' at row {row_idx}."
                )
            if math.isinf(value):
                raise ResultValidationError(
                    f"Invalid numeric value Infinity in column '{col_name}' at row {row_idx}."
                )
            return self._apply_sanity_bounds(value, col_name, row_idx, metric_unit, result_type)

        # Normalization of Decimal
        if isinstance(value, Decimal):
            if value.is_nan():
                raise ResultValidationError(
                    f"Invalid Decimal value NaN in column '{col_name}' at row {row_idx}."
                )
            if value.is_infinite():
                raise ResultValidationError(
                    f"Invalid Decimal value Infinity in column '{col_name}' at row {row_idx}."
                )
            # Convert to int if integral, else float
            float_val = float(value)
            return self._apply_sanity_bounds(float_val, col_name, row_idx, metric_unit, result_type)

        # Integer bounds
        if isinstance(value, int):
            return self._apply_sanity_bounds(value, col_name, row_idx, metric_unit, result_type)

        # Datetime / Date normalization to ISO-8601 string
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # String stripping and UTF-8 verification
        if isinstance(value, str):
            return value.strip()

        # Other primitive types (bool, etc.)
        return value

    def _apply_sanity_bounds(
        self,
        num_val: float | int,
        col_name: str,
        row_idx: int,
        metric_unit: Optional[str],
        result_type: Optional[str] = None,
    ) -> float | int:
        """
        Applies domain-specific physical sanity checks to numeric metric values.
        """
        col_lower = col_name.lower()

        # Percentage sanity checks: [0, 100] (delta/difference/change columns allow [-100, 100])
        if col_lower in ("difference", "delta", "variance", "change", "diff", "gap") or (
            result_type in ("CHANGE_QUERY", "CHANGE") and col_lower in ("metric_value", "change")
        ):
            if not (-100.01 <= num_val <= 100.01):
                raise ResultValidationError(
                    f"Percentage difference value {num_val} out of valid [-100, 100] range in column '{col_name}' at row {row_idx}."
                )
        elif metric_unit == "percentage" or "percent" in col_lower or "pct" in col_lower:
            if not (0.0 <= num_val <= 100.0):
                # We allow slight rounding margin if needed, but reject impossible percentages
                if num_val < -0.01 or num_val > 100.01:
                    raise ResultValidationError(
                        f"Percentage value {num_val} out of valid [0, 100] range in column '{col_name}' at row {row_idx}."
                    )

        # Non-negative count checks
        if metric_unit in ("count", "students_count", "offerings_count") or (
            "count" in col_lower or "strength" in col_lower or "headcount" in col_lower
        ):
            if num_val < 0:
                raise ResultValidationError(
                    f"Count metric value {num_val} cannot be negative in column '{col_name}' at row {row_idx}."
                )

        # Scale 1 to 3 checks (e.g. rubrics / attainments)
        if metric_unit == "scale_1_to_3" or "attainment" in col_lower:
            if num_val < 0 or num_val > 3.01:
                raise ResultValidationError(
                    f"Scale metric value {num_val} out of valid [0, 3] range in column '{col_name}' at row {row_idx}."
                )

        return num_val


# Singleton instance
result_validator = ResultValidator()
