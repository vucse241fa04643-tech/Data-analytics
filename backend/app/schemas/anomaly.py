"""Agent 63 - Phase 11: Anomaly Detection Schemas
Pydantic schemas for deterministic anomaly assessment on validated query results.

CRITICAL SECURITY INVARIANTS:
- Operates strictly on already-authorized and validated QueryResults.
- Never exposes internal database details, table names, SQL, credentials, or authorization internals.
- Enforces strict three-state model: NO_ANOMALY, ANOMALY_DETECTED, ASSESSMENT_UNAVAILABLE.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AnomalyStatus(str, Enum):
    """Authoritative three-state assessment lifecycle."""
    NO_ANOMALY = "NO_ANOMALY"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    ASSESSMENT_UNAVAILABLE = "ASSESSMENT_UNAVAILABLE"


class AnomalySeverity(str, Enum):
    """Deterministic severity classification levels."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyMethod(str, Enum):
    """Supported deterministic anomaly detection methods."""
    NONE = "NONE"
    TARGET_DEVIATION = "TARGET_DEVIATION"
    CONFIGURED_THRESHOLD = "CONFIGURED_THRESHOLD"
    PERCENTAGE_DEVIATION = "PERCENTAGE_DEVIATION"
    HISTORICAL_Z_SCORE = "HISTORICAL_Z_SCORE"
    CROSS_CATEGORY_IQR = "CROSS_CATEGORY_IQR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class BaselineType(str, Enum):
    """Authoritative classification of baseline or threshold provenance."""
    OFFICIAL_TARGET = "OFFICIAL_TARGET"
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"
    ANALYTICAL_HEURISTIC = "ANALYTICAL_HEURISTIC"
    NO_BASELINE = "NO_BASELINE"


class CategoryAnomalyItem(BaseModel):
    """Deterministic anomaly details for an individual category within multi-category results."""
    category_name: str = Field(..., description="Name of the evaluated category (e.g., department code)")
    observed_value: float = Field(..., description="Observed numeric value for this category")
    baseline_or_benchmark: Optional[float] = Field(default=None, description="Benchmark or cross-category median")
    deviation: Optional[float] = Field(default=None, description="Difference between observed value and baseline")
    severity: AnomalySeverity = Field(default=AnomalySeverity.NONE, description="Deterministic category severity")
    explanation: str = Field(..., description="Factual factual explanation of category anomaly")


class AnomalyAssessment(BaseModel):
    """Deterministic anomaly assessment report generated from validated QueryResults."""
    status: AnomalyStatus = Field(
        ...,
        description="Three-state status: NO_ANOMALY, ANOMALY_DETECTED, or ASSESSMENT_UNAVAILABLE"
    )
    detected: bool = Field(
        default=False,
        description="True if and only if status is ANOMALY_DETECTED"
    )
    severity: AnomalySeverity = Field(
        default=AnomalySeverity.NONE,
        description="Deterministic severity level: NONE, LOW, MEDIUM, HIGH"
    )
    method: AnomalyMethod = Field(
        default=AnomalyMethod.NONE,
        description="Deterministic anomaly detection method applied"
    )
    metric_id: str = Field(..., description="Canonical metric ID evaluated")
    metric_display_name: Optional[str] = Field(default=None, description="Human-readable metric name")
    observed_value: Optional[float] = Field(default=None, description="Observed primary numeric value")
    baseline_value: Optional[float] = Field(default=None, description="Authoritative baseline or configured benchmark")
    baseline_type: BaselineType = Field(
        default=BaselineType.NO_BASELINE,
        description="Provenance of the baseline: OFFICIAL_TARGET, HISTORICAL_BASELINE, ANALYTICAL_HEURISTIC, or NO_BASELINE"
    )
    deviation_value: Optional[float] = Field(default=None, description="Absolute difference (observed - baseline)")
    deviation_percentage: Optional[float] = Field(default=None, description="Percentage deviation relative to baseline")
    confidence: Optional[str] = Field(default=None, description="Deterministic confidence or evidence strength")
    explanation: Optional[str] = Field(default=None, description="Factual deterministic explanation without causal claims")
    limitations: Optional[str] = Field(default=None, description="Analytical limitations, sample size notes, or data bounds")
    supporting_scope: Optional[str] = Field(default=None, description="Institutional scope context (e.g. department, cohort)")
    requires_review: bool = Field(default=False, description="Whether this anomaly warrants institutional review")
    category_anomalies: List[CategoryAnomalyItem] = Field(
        default_factory=list,
        description="Outlier categories if evaluated across categorical breakdown"
    )
