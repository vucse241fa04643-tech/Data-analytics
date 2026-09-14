"""Agent 63 - Phase 11: Deterministic Anomaly Detection Service
Analyzes ONLY already-authorized and already-validated QueryResults.

CRITICAL SECURITY INVARIANTS:
- Operates strictly on validated QueryResults.
- Absolutely ZERO database access (no PostgreSQL calls, no psycopg, no connections).
- Absolutely ZERO SQL generation or manipulation.
- Absolutely ZERO LLM calls (no Groq, Gemini, or external API invocations).
- Strictly deterministic: identical validated QueryResult + config -> identical assessment.
- Explanations are factual, objective, and explicitly disclaim unsupported causal claims.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.schemas.anomaly import (
    AnomalyAssessment,
    AnomalyMethod,
    AnomalySeverity,
    AnomalyStatus,
    BaselineType,
    CategoryAnomalyItem,
)
from backend.app.schemas.query_result import QueryResult, QueryResultStatus
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)

logger = get_logger("agent63.services.anomaly")

# Approved semantic metrics supporting anomaly detection
SUPPORTED_ANOMALY_METRICS = {
    "attendance.percentage",
    "attendance.raw_percentage",
    "attendance.course_aggregate",
    "attendance.section_aggregate",
    "assessment.course_pass_percentage",
    "assessment.average_total_marks",
    "assessment.failure_count",
    "outcomes.co_attainment_level",
    "outcomes.po_attainment_level",
    "outcomes.co_attaining_percentage",
    "placement.average_ctc",
    "placement.highest_ctc",
    "placement.placed_students_count",
    "placement.readiness_average_score",
    "quality.kpi_latest_value",
    "quality.kpi_target_variance",
}

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


class AnomalyDetectionService:
    """Deterministic, in-memory anomaly assessment service for validated institutional query results."""

    def __init__(self, semantic_registry: Optional[SemanticRegistryService] = None):
        self._semantic_registry = semantic_registry or get_semantic_registry_service()

    def _get_metric_meta(self, metric_id: str) -> Tuple[str, Optional[str]]:
        """Resolves display name and unit from Phase 4 semantic registry."""
        metric = self._semantic_registry.get_metric(metric_id)
        if metric:
            return metric.get("display_name", metric_id), metric.get("unit")
        clean_name = metric_id.split(".")[-1].replace("_", " ").title()
        return clean_name, None

    def _extract_metric_column(
        self, query_result: QueryResult, metric_id: str
    ) -> Optional[str]:
        """Identifies the primary numeric metric column from the result columns."""
        cols = query_result.columns
        if not cols:
            return None

        # Direct canonical name match
        canonical_name = metric_id.split(".")[-1]
        for col in cols:
            if col == canonical_name or col == metric_id:
                return col

        # Common metric column names
        metric_candidates = [
            "value",
            "metric_value",
            "avg_attendance",
            "adjusted_pct",
            "pass_percentage",
            "pass_pct",
            "co_level",
            "po_level",
            "ctc",
            "average_ctc",
            "highest_ctc",
            "variance_pct",
            "students_count",
            "count",
        ]
        for candidate in metric_candidates:
            if candidate in cols:
                return candidate

        # Find first numeric column if possible
        if query_result.rows:
            sample_row = query_result.rows[0]
            for col in cols:
                val = sample_row.get(col)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    return col

        return cols[-1] if cols else None

    def _extract_dimension_column(
        self, query_result: QueryResult, metric_col: str
    ) -> Optional[str]:
        """Identifies the categorical or temporal dimension column in the result set."""
        for col in query_result.columns:
            if col != metric_col and not col.startswith("_"):
                return col
        return None

    def _is_numeric(self, val: Any) -> bool:
        """Determines if a value is a valid finite float or int."""
        if val is None or isinstance(val, bool):
            return False
        if isinstance(val, (int, float)):
            return not (math.isnan(val) or math.isinf(val))
        try:
            f = float(val)
            return not (math.isnan(f) or math.isinf(f))
        except (ValueError, TypeError):
            return False

    def assess_result(
        self,
        query_result: QueryResult,
        intent: Dict[str, Any],
        metric_id: str,
    ) -> AnomalyAssessment:
        """
        Performs 100% deterministic anomaly assessment on a validated QueryResult.
        
        Guarantees:
        - NEVER queries the database.
        - NEVER generates SQL.
        - NEVER calls any LLM.
        - Returns one of three states: NO_ANOMALY, ANOMALY_DETECTED, ASSESSMENT_UNAVAILABLE.
        """
        display_name, unit = self._get_metric_meta(metric_id)
        raw_scope = intent.get("filters", {}).get("department")
        if isinstance(raw_scope, list):
            scope = " vs ".join(str(d) for d in raw_scope)
        else:
            scope = (
                raw_scope
                or intent.get("filters", {}).get("academic_year")
                or "Institutional"
            )

        # 1. Verification of Metric Capability
        if metric_id not in SUPPORTED_ANOMALY_METRICS:
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.NONE,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations="Metric does not support automated anomaly assessment.",
            )

        # 2. Check for empty or unexecuted query results
        if query_result.status != QueryResultStatus.SUCCESS or not query_result.rows:
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.NONE,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations="Anomaly assessment unavailable for empty or unexecuted query results.",
            )

        # 3. Locate Metric and Dimension Columns
        metric_col = self._extract_metric_column(query_result, metric_id)
        if not metric_col:
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.NONE,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations="Unable to identify a numeric metric column in the validated result set.",
            )

        dim_col = self._extract_dimension_column(query_result, metric_col)

        # 4. Check for NULL, NaN, or Infinite Values in Metric Column
        raw_values = [row.get(metric_col) for row in query_result.rows]
        if any(not self._is_numeric(v) for v in raw_values):
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.NONE,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations="Anomaly assessment unavailable because one or more values are NULL, NaN, infinite, or non-numeric.",
            )

        numeric_values = [float(v) for v in raw_values]

        # 5. Check for Multidimensional / Incompatible Shape (> 2 non-internal columns)
        non_metric_cols = [
            c for c in query_result.columns if c != metric_col and not c.startswith("_")
        ]
        if len(non_metric_cols) > 1:
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.NONE,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations="Multidimensional results with multiple grouping keys are not currently supported for automated anomaly detection.",
            )

        # 6. Branch on Result Shape
        # Shape A: Single numeric KPI (1 row)
        if len(query_result.rows) == 1:
            return self._assess_single_kpi(
                observed=numeric_values[0],
                row=query_result.rows[0],
                metric_id=metric_id,
                display_name=display_name,
                scope=scope,
            )

        # Check if dimension is temporal (Time Series) or categorical
        is_temporal = bool(
            dim_col and any(t in dim_col.lower() for t in TEMPORAL_DIMENSIONS)
        )

        # Shape C: Time Series
        if is_temporal:
            return self._assess_time_series(
                values=numeric_values,
                rows=query_result.rows,
                dim_col=dim_col,
                metric_id=metric_id,
                display_name=display_name,
                scope=scope,
            )

        # Shape B: Categorical Breakdown
        return self._assess_categorical(
            values=numeric_values,
            rows=query_result.rows,
            dim_col=dim_col or "category",
            metric_id=metric_id,
            display_name=display_name,
            scope=scope,
        )

    def _assess_single_kpi(
        self,
        observed: float,
        row: Dict[str, Any],
        metric_id: str,
        display_name: str,
        scope: str,
    ) -> AnomalyAssessment:
        """Evaluates single-row KPI results against targets or configured analytical thresholds."""
        # Method B: Target Deviation (if target or variance_pct exists in validated row)
        target_val = None
        for k, v in row.items():
            if "target" in k.lower() and self._is_numeric(v):
                target_val = float(v)
                break

        if metric_id == "quality.kpi_target_variance" or target_val is not None:
            if target_val is not None:
                dev = observed - target_val
                dev_pct = round((dev / target_val) * 100.0, 2) if target_val != 0 else 0.0
            else:
                # Metric is variance_pct directly
                dev = observed
                dev_pct = observed

            if dev_pct < -5.0:
                abs_pct = abs(dev_pct)
                severity = (
                    AnomalySeverity.HIGH
                    if abs_pct >= 30.0
                    else (AnomalySeverity.MEDIUM if abs_pct >= 15.0 else AnomalySeverity.LOW)
                )
                target_display = f"of {target_val:.1f}" if target_val is not None else "target"
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=severity,
                    method=AnomalyMethod.TARGET_DEVIATION,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(observed, 2),
                    baseline_value=round(target_val, 2) if target_val is not None else None,
                    baseline_type=BaselineType.OFFICIAL_TARGET,
                    deviation_value=round(dev, 2),
                    deviation_percentage=round(dev_pct, 2),
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. {display_name} is {abs_pct:.1f}% below the official institutional target "
                        f"{target_display} based on an analytical deviation parameter of 5.0%. "
                        f"The result does not establish the cause."
                    ),
                    limitations="Target sourced from official institutional KPI definition in validated query result. The 5.0% threshold is an analytical detection parameter and is not an official institutional policy.",
                    supporting_scope=scope,
                    requires_review=(severity in (AnomalySeverity.MEDIUM, AnomalySeverity.HIGH)),
                )
            else:
                return AnomalyAssessment(
                    status=AnomalyStatus.NO_ANOMALY,
                    detected=False,
                    severity=AnomalySeverity.NONE,
                    method=AnomalyMethod.TARGET_DEVIATION,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(observed, 2),
                    baseline_value=round(target_val, 2) if target_val is not None else None,
                    baseline_type=BaselineType.OFFICIAL_TARGET,
                    deviation_value=round(dev, 2),
                    deviation_percentage=round(dev_pct, 2),
                    confidence="HIGH",
                    explanation=f"{display_name} is within the acceptable 5.0% analytical tolerance parameter of the official institutional target.",
                    supporting_scope=scope,
                )

        # Method A: Configured Analytical Threshold
        # Explicit distinction: analytical heuristic, NOT institutional policy or official benchmark
        if "attendance" in metric_id:
            benchmark = settings.ANOMALY_ATTENDANCE_THRESHOLD
            if observed < benchmark:
                diff = round(observed - benchmark, 2)
                severity = (
                    AnomalySeverity.HIGH
                    if diff <= -15.0
                    else (AnomalySeverity.MEDIUM if diff <= -5.0 else AnomalySeverity.LOW)
                )
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=severity,
                    method=AnomalyMethod.CONFIGURED_THRESHOLD,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(observed, 2),
                    baseline_value=benchmark,
                    baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                    deviation_value=diff,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. The observed value is below the configured analytical detection threshold of {benchmark:.1f}%. "
                        f"This threshold is an analytical heuristic and is not an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations="Evaluated against a configured analytical heuristic (75%); does not represent an official institutional policy or statutory requirement.",
                    supporting_scope=scope,
                    requires_review=True,
                )
            return AnomalyAssessment(
                status=AnomalyStatus.NO_ANOMALY,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.CONFIGURED_THRESHOLD,
                metric_id=metric_id,
                metric_display_name=display_name,
                observed_value=round(observed, 2),
                baseline_value=benchmark,
                baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                explanation=(
                    f"The observed value of {observed:.1f}% meets or exceeds the configured analytical detection threshold of {benchmark:.1f}%. "
                    f"This threshold is an analytical heuristic and is not an official institutional policy."
                ),
                supporting_scope=scope,
            )

        if "pass_percentage" in metric_id:
            benchmark = settings.ANOMALY_PASS_RATE_THRESHOLD
            if observed < benchmark:
                diff = round(observed - benchmark, 2)
                severity = (
                    AnomalySeverity.HIGH
                    if diff <= -20.0
                    else (AnomalySeverity.MEDIUM if diff <= -10.0 else AnomalySeverity.LOW)
                )
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=severity,
                    method=AnomalyMethod.CONFIGURED_THRESHOLD,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(observed, 2),
                    baseline_value=benchmark,
                    baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                    deviation_value=diff,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. The observed course pass percentage of {observed:.1f}% is below the configured analytical detection threshold of {benchmark:.1f}%. "
                        f"This threshold is an analytical heuristic and is not an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations="Evaluated against a configured analytical heuristic (60%); does not represent an official institutional policy or statutory requirement.",
                    supporting_scope=scope,
                    requires_review=True,
                )
            return AnomalyAssessment(
                status=AnomalyStatus.NO_ANOMALY,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.CONFIGURED_THRESHOLD,
                metric_id=metric_id,
                metric_display_name=display_name,
                observed_value=round(observed, 2),
                baseline_value=benchmark,
                baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                explanation=(
                    f"Course pass percentage of {observed:.1f}% meets or exceeds the configured analytical detection threshold of {benchmark:.1f}%. "
                    f"This threshold is an analytical heuristic and is not an official institutional policy."
                ),
                supporting_scope=scope,
            )

        if "attainment" in metric_id:
            benchmark = settings.ANOMALY_ATTAINMENT_THRESHOLD
            if observed < benchmark:
                diff = round(observed - benchmark, 2)
                severity = (
                    AnomalySeverity.HIGH
                    if diff <= -0.8
                    else (AnomalySeverity.MEDIUM if diff <= -0.4 else AnomalySeverity.LOW)
                )
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=severity,
                    method=AnomalyMethod.CONFIGURED_THRESHOLD,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(observed, 2),
                    baseline_value=benchmark,
                    baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                    deviation_value=diff,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. Outcome attainment level of {observed:.2f} is below the configured analytical detection threshold of {benchmark:.2f} (on a 3-point scale). "
                        f"This threshold is an analytical heuristic and is not an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations="Evaluated against a configured analytical heuristic (2.0); does not represent an official institutional policy or statutory requirement.",
                    supporting_scope=scope,
                    requires_review=True,
                )
            return AnomalyAssessment(
                status=AnomalyStatus.NO_ANOMALY,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.CONFIGURED_THRESHOLD,
                metric_id=metric_id,
                metric_display_name=display_name,
                observed_value=round(observed, 2),
                baseline_value=benchmark,
                baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                explanation=(
                    f"Attainment level of {observed:.2f} meets or exceeds the configured analytical detection threshold of {benchmark:.2f}. "
                    f"This threshold is an analytical heuristic and is not an official institutional policy."
                ),
                supporting_scope=scope,
            )

        # For uncalibrated single-row metrics without an authoritative baseline in result
        return AnomalyAssessment(
            status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
            detected=False,
            severity=AnomalySeverity.NONE,
            method=AnomalyMethod.NONE,
            metric_id=metric_id,
            metric_display_name=display_name,
            observed_value=round(observed, 2),
            baseline_type=BaselineType.NO_BASELINE,
            supporting_scope=scope,
            limitations="No authoritative baseline or official target is present in the validated query result for this metric.",
        )

    def _assess_time_series(
        self,
        values: List[float],
        rows: List[Dict[str, Any]],
        dim_col: str,
        metric_id: str,
        display_name: str,
        scope: str,
    ) -> AnomalyAssessment:
        """Evaluates historical observations using deterministic statistical deviation (z-score)."""
        min_obs = settings.ANOMALY_HISTORICAL_MIN_OBSERVATIONS
        if len(values) < min_obs:
            return AnomalyAssessment(
                status=AnomalyStatus.ASSESSMENT_UNAVAILABLE,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.INSUFFICIENT_DATA,
                metric_id=metric_id,
                metric_display_name=display_name,
                supporting_scope=scope,
                limitations=f"Insufficient historical data to determine an anomaly ({len(values)} observed, minimum {min_obs} required).",
            )

        # Calculate historical mean and standard deviation of baseline (all prior points or all points)
        baseline_vals = values[:-1] if len(values) >= 4 else values
        mean_val = sum(baseline_vals) / len(baseline_vals)
        variance = sum((x - mean_val) ** 2 for x in baseline_vals) / len(baseline_vals)
        std_val = math.sqrt(variance)

        latest_val = values[-1]
        latest_label = str(rows[-1].get(dim_col, "latest period"))

        if std_val > 0.0:
            z_score = (latest_val - mean_val) / std_val
            z_threshold = settings.ANOMALY_Z_SCORE_THRESHOLD

            if abs(z_score) >= z_threshold:
                severity = (
                    AnomalySeverity.HIGH
                    if abs(z_score) >= 3.0
                    else (AnomalySeverity.MEDIUM if abs(z_score) >= 2.5 else AnomalySeverity.LOW)
                )
                dev_val = round(latest_val - mean_val, 2)
                dev_pct = round((dev_val / mean_val) * 100.0, 2) if mean_val != 0 else 0.0
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=severity,
                    method=AnomalyMethod.HISTORICAL_Z_SCORE,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(latest_val, 2),
                    baseline_value=round(mean_val, 2),
                    baseline_type=BaselineType.HISTORICAL_BASELINE,
                    deviation_value=dev_val,
                    deviation_percentage=dev_pct,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. Latest observation ({latest_label}: {latest_val:.1f}) exhibits a "
                        f"significant statistical deviation (z-score: {z_score:.2f}) from the historical baseline mean of {mean_val:.1f}. "
                        f"This baseline is derived from {len(baseline_vals)} authorized historical periods and does not represent an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations=f"Calculated from {len(baseline_vals)} authorized historical periods in the validated result set.",
                    supporting_scope=scope,
                    requires_review=True,
                )
            else:
                return AnomalyAssessment(
                    status=AnomalyStatus.NO_ANOMALY,
                    detected=False,
                    severity=AnomalySeverity.NONE,
                    method=AnomalyMethod.HISTORICAL_Z_SCORE,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(latest_val, 2),
                    baseline_value=round(mean_val, 2),
                    baseline_type=BaselineType.HISTORICAL_BASELINE,
                    deviation_value=round(latest_val - mean_val, 2),
                    confidence="HIGH",
                    explanation=f"Latest observation ({latest_label}: {latest_val:.1f}) is within normal historical statistical variation (z-score: {z_score:.2f}, baseline mean: {mean_val:.1f}).",
                    supporting_scope=scope,
                )
        else:
            # Historical variance is 0
            if abs(latest_val - mean_val) > 0.001:
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=AnomalySeverity.MEDIUM,
                    method=AnomalyMethod.PERCENTAGE_DEVIATION,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    observed_value=round(latest_val, 2),
                    baseline_value=round(mean_val, 2),
                    baseline_type=BaselineType.HISTORICAL_BASELINE,
                    deviation_value=round(latest_val - mean_val, 2),
                    confidence="MEDIUM",
                    explanation=f"Potential anomaly detected. Value changed from completely flat historical baseline of {mean_val:.1f} to {latest_val:.1f}. This baseline is derived from authorized historical observations. The result does not establish the cause.",
                    supporting_scope=scope,
                    requires_review=True,
                )
            return AnomalyAssessment(
                status=AnomalyStatus.NO_ANOMALY,
                detected=False,
                severity=AnomalySeverity.NONE,
                method=AnomalyMethod.HISTORICAL_Z_SCORE,
                metric_id=metric_id,
                metric_display_name=display_name,
                observed_value=round(latest_val, 2),
                baseline_value=round(mean_val, 2),
                baseline_type=BaselineType.HISTORICAL_BASELINE,
                explanation="Values remain strictly consistent across all historical observations.",
                supporting_scope=scope,
            )

    def _assess_categorical(
        self,
        values: List[float],
        rows: List[Dict[str, Any]],
        dim_col: str,
        metric_id: str,
        display_name: str,
        scope: str,
    ) -> AnomalyAssessment:
        """Evaluates categorical breakdown results using cross-category IQR and benchmark thresholds."""
        n = len(values)
        category_anomalies: List[CategoryAnomalyItem] = []

        # When >= 4 categories, calculate IQR distribution
        if n >= 4:
            sorted_vals = sorted(values)
            # Quartiles
            q1_idx = int(n * 0.25)
            q3_idx = int(n * 0.75)
            med_idx = int(n * 0.5)
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            median_val = sorted_vals[med_idx]
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            for row, val in zip(rows, values):
                cat_name = str(row.get(dim_col, "Unknown"))
                if iqr > 0 and (val < lower_bound or val > upper_bound):
                    diff = val - median_val
                    severity = (
                        AnomalySeverity.HIGH
                        if abs(diff) > 2.0 * iqr
                        else AnomalySeverity.MEDIUM
                    )
                    category_anomalies.append(
                        CategoryAnomalyItem(
                            category_name=cat_name,
                            observed_value=round(val, 2),
                            baseline_or_benchmark=round(median_val, 2),
                            deviation=round(diff, 2),
                            severity=severity,
                            explanation=f"{cat_name} ({val:.1f}) is an outlier relative to cross-category distribution (median: {median_val:.1f}).",
                        )
                    )

            if category_anomalies:
                highest_severity = max(
                    (a.severity for a in category_anomalies),
                    key=lambda s: ["NONE", "LOW", "MEDIUM", "HIGH"].index(s.value),
                )
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=highest_severity,
                    method=AnomalyMethod.CROSS_CATEGORY_IQR,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    baseline_value=round(median_val, 2),
                    baseline_type=BaselineType.HISTORICAL_BASELINE,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. {len(category_anomalies)} outlier category(ies) detected based on "
                        f"cross-sectional statistical distribution (median: {median_val:.1f}). "
                        f"This distribution is an empirical observation across authorized records and does not represent an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations=f"Evaluated across {n} comparable categories in the validated result set.",
                    supporting_scope=scope,
                    requires_review=True,
                    category_anomalies=category_anomalies,
                )

        # Fallback: check individual categories against configured benchmark (e.g. attendance < 75%)
        benchmark = None
        if "attendance" in metric_id:
            benchmark = settings.ANOMALY_ATTENDANCE_THRESHOLD
        elif "pass_percentage" in metric_id:
            benchmark = settings.ANOMALY_PASS_RATE_THRESHOLD
        elif "attainment" in metric_id:
            benchmark = settings.ANOMALY_ATTAINMENT_THRESHOLD

        if benchmark is not None:
            for row, val in zip(rows, values):
                cat_name = str(row.get(dim_col, "Unknown"))
                if val < benchmark:
                    diff = round(val - benchmark, 2)
                    severity = (
                        AnomalySeverity.HIGH
                        if diff <= -15.0
                        else (AnomalySeverity.MEDIUM if diff <= -5.0 else AnomalySeverity.LOW)
                    )
                    category_anomalies.append(
                        CategoryAnomalyItem(
                            category_name=cat_name,
                            observed_value=round(val, 2),
                            baseline_or_benchmark=benchmark,
                            deviation=diff,
                            severity=severity,
                            explanation=f"{cat_name} ({val:.1f}) is {abs(diff):.1f} below the analytical heuristic ({benchmark:.1f}).",
                        )
                    )

            if category_anomalies:
                highest_severity = max(
                    (a.severity for a in category_anomalies),
                    key=lambda s: ["NONE", "LOW", "MEDIUM", "HIGH"].index(s.value),
                )
                return AnomalyAssessment(
                    status=AnomalyStatus.ANOMALY_DETECTED,
                    detected=True,
                    severity=highest_severity,
                    method=AnomalyMethod.CONFIGURED_THRESHOLD,
                    metric_id=metric_id,
                    metric_display_name=display_name,
                    baseline_value=benchmark,
                    baseline_type=BaselineType.ANALYTICAL_HEURISTIC,
                    confidence="HIGH",
                    explanation=(
                        f"Potential anomaly detected. {len(category_anomalies)} of {n} categories are below the configured analytical detection threshold "
                        f"of {benchmark:.1f}%. This threshold is an analytical heuristic and is not an official institutional policy. "
                        f"The result does not establish the cause."
                    ),
                    limitations="Evaluated against a configured analytical heuristic; does not represent an official institutional policy or statutory requirement.",
                    supporting_scope=scope,
                    requires_review=True,
                    category_anomalies=category_anomalies,
                )

        baseline_type = (
            BaselineType.HISTORICAL_BASELINE
            if n >= 4
            else (BaselineType.ANALYTICAL_HEURISTIC if benchmark is not None else BaselineType.NO_BASELINE)
        )
        return AnomalyAssessment(
            status=AnomalyStatus.NO_ANOMALY,
            detected=False,
            severity=AnomalySeverity.NONE,
            method=AnomalyMethod.CROSS_CATEGORY_IQR if n >= 4 else AnomalyMethod.CONFIGURED_THRESHOLD,
            metric_id=metric_id,
            metric_display_name=display_name,
            baseline_type=baseline_type,
            explanation=f"All {n} categories lie within normal statistical distribution and configured analytical heuristics.",
            supporting_scope=scope,
        )


_singleton_anomaly_service: Optional[AnomalyDetectionService] = None


def get_anomaly_service() -> AnomalyDetectionService:
    """Dependency injection provider for AnomalyDetectionService."""
    global _singleton_anomaly_service
    if _singleton_anomaly_service is None:
        _singleton_anomaly_service = AnomalyDetectionService()
    return _singleton_anomaly_service
