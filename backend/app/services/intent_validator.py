"""
Agent 63 – Structured Intent Validator
Enforces semantic catalog grounding, lifecycle status gatekeeping (APPROVED only),
dimension validity, confidential domain isolation, and strict semantic filter allowlisting.
Zero SQL or arbitrary database columns permitted.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from backend.app.core.errors import IntentValidationError
from backend.app.core.logging import get_logger
from backend.app.schemas.intent import IntentType, IntentValidationStatus, StructuredIntent
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)

logger = get_logger("agent63.services.intent_validator")

# Strictly denied schemas and objects quarantined from analytics
STRICTLY_DENIED_PREFIXES = [
    "confidential.",
    "assessment.question_paper",
    "exams.question_paper_delivery",
    "exams.malpractice_incident",
]


class IntentValidationResult(BaseModel):
    """Result envelope from intent validation step."""
    is_valid: bool
    status: IntentValidationStatus
    error_code: Optional[str] = None
    message: str = ""
    validated_intent: Optional[StructuredIntent] = None
    clarification_questions: List[str] = Field(default_factory=list)


class IntentValidator:
    """Validates structured intents against the Phase 4 Semantic Layer."""

    def __init__(self, semantic_registry: Optional[SemanticRegistryService] = None):
        self._registry = semantic_registry or get_semantic_registry_service()

    def get_allowed_filter_keys_for_metric(self, metric: Dict[str, Any]) -> Set[str]:
        """
        Dynamically computes all permitted filter keys for a metric from its Phase 4 semantic definition.
        Grounded strictly in metric.allowed_filters, metric.allowed_dimensions, and time_semantics.
        Rejects any arbitrary database columns or non-semantic attributes.
        """
        allowed: Set[str] = set()

        # 1. Explicit allowed_filters declared on the metric definition
        for f in metric.get("allowed_filters", []) or []:
            if not f:
                continue
            f_lower = str(f).strip().lower()
            allowed.add(f_lower)
            if f_lower.endswith("_id"):
                base = f_lower[:-3]
                allowed.add(base)
                allowed.add(f"{base}s")

        # 2. Dimensions explicitly allowed for this metric
        allowed_dim_ids = set(metric.get("allowed_dimensions", []) or [])
        for dim_id in allowed_dim_ids:
            if not dim_id:
                continue
            dim = self._registry.get_dimension(dim_id)
            if dim:
                c_name = str(dim.get("canonical_name") or "").strip().lower()
                d_id = str(dim.get("dimension_id") or "").strip().lower()
                key_col = str(dim.get("key_column") or "").strip().lower()
                code_col = str(dim.get("code_column") or "").strip().lower()

                if c_name:
                    allowed.add(c_name)
                    allowed.add(f"{c_name}s")
                    allowed.add(f"{c_name}_id")
                    allowed.add(f"{c_name}_code")
                if d_id:
                    allowed.add(d_id)
                if key_col:
                    allowed.add(key_col)
                if code_col:
                    allowed.add(code_col)

        # 3. Temporal parameters if metric has time_semantics
        time_sem = metric.get("time_semantics") or {}
        if isinstance(time_sem, dict) and time_sem:
            time_dim_id = time_sem.get("time_dimension")
            if time_dim_id:
                t_dim = self._registry.get_dimension(time_dim_id)
                if t_dim:
                    tc_name = str(t_dim.get("canonical_name") or "").strip().lower()
                    if tc_name:
                        allowed.add(tc_name)
                        allowed.add(f"{tc_name}s")
                        allowed.add(f"{tc_name}_id")
            time_col = time_sem.get("time_column")
            if time_col:
                allowed.add(str(time_col).strip().lower())
            period_grain = time_sem.get("period_grain")
            if period_grain:
                allowed.add(str(period_grain).strip().lower())

            # Standard academic temporal filters
            allowed.add("academic_year")
            allowed.add("academic_years")
            allowed.add("term")
            allowed.add("terms")

        return allowed

    def validate_intent(self, intent: StructuredIntent) -> IntentValidationResult:
        """
        Executes multi-stage validation:
        1. Intent type classification
        2. Metric existence and lifecycle status (APPROVED only)
        3. Confidential and restricted object containment
        4. Dimension catalog and metric-permission verification
        5. Semantic filter allowlisting and SQL defense-in-depth
        """
        # 1. Out-of-Scope check
        if intent.intent_type == IntentType.OUT_OF_SCOPE:
            logger.info("Intent classified as OUT_OF_SCOPE")
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.OUT_OF_SCOPE,
                error_code="OUT_OF_SCOPE",
                message=(
                    "This inquiry is outside the scope of Agent 63 institutional data analytics. "
                    "Please submit questions regarding student attendance, assessment performance, "
                    "course outcomes, curriculum attainment, or campus placements."
                ),
            )

        # 2. Clarification Needed check
        if intent.intent_type == IntentType.CLARIFICATION_NEEDED:
            logger.info("Intent requires clarification")
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.CLARIFICATION_REQUIRED,
                error_code="CLARIFICATION_REQUIRED",
                message="The analytical question is ambiguous and requires clarification before execution.",
                clarification_questions=[
                    "Which academic department or programme would you like to analyze?",
                    "Which academic year or term period should be included?",
                ],
            )

        # 3. Unsupported intent check
        if intent.intent_type == IntentType.UNSUPPORTED:
            logger.info("Intent classified as UNSUPPORTED")
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.REJECTED,
                error_code="UNSUPPORTED_INTENT",
                message="The requested analytical operation cannot be mapped to supported institutional query archetypes.",
            )

        # 4. Metric ID Validation
        if not intent.metric_id:
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.REJECTED,
                error_code="MISSING_PRIMARY_METRIC",
                message="Could not resolve a specific institutional metric from the inquiry.",
                clarification_questions=["Which metric would you like to query (e.g. attendance percentage, pass percentage, placement offers)?"],
            )

        metric = self._registry.get_metric(intent.metric_id)
        if not metric:
            logger.warning(f"Intent validation rejected unknown metric: {intent.metric_id}")
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.REJECTED,
                error_code="METRIC_NOT_FOUND",
                message=f"Metric '{intent.metric_id}' does not exist in the institutional Semantic Catalog.",
            )

        # 5. Metric Lifecycle Gatekeeping (APPROVED only)
        metric_status = metric.get("status", "DRAFT")
        if metric_status != "APPROVED":
            logger.warning(
                f"Intent validation rejected non-approved metric: {intent.metric_id} (status={metric_status})"
            )
            return IntentValidationResult(
                is_valid=False,
                status=IntentValidationStatus.REJECTED,
                error_code="METRIC_NOT_APPROVED",
                message=(
                    f"Metric '{intent.metric_id}' is currently in '{metric_status}' status "
                    "and is strictly excluded from production analytics planning."
                ),
            )

        # Validate secondary metrics if present
        for sec_id in intent.secondary_metric_ids:
            sec_metric = self._registry.get_metric(sec_id)
            if not sec_metric:
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="METRIC_NOT_FOUND",
                    message=f"Secondary metric '{sec_id}' does not exist in the institutional Semantic Catalog.",
                )
            if sec_metric.get("status") != "APPROVED":
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="METRIC_NOT_APPROVED",
                    message=f"Secondary metric '{sec_id}' is in non-approved status '{sec_metric.get('status')}'.",
                )

        # 6. Confidential & Restricted Schema Lockdown
        for src_obj in metric.get("source_objects", []):
            for denied_prefix in STRICTLY_DENIED_PREFIXES:
                if src_obj.startswith(denied_prefix):
                    logger.critical(f"Intent references denied resource: {src_obj}")
                    return IntentValidationResult(
                        is_valid=False,
                        status=IntentValidationStatus.REJECTED,
                        error_code="RESTRICTED_RESOURCE",
                        message="Requested resource is strictly quarantined from institutional analytics.",
                    )

        # Also scan filters for attempted confidential injections
        for f_key, f_val in intent.filters.items():
            f_str = f"{f_key} {f_val}".lower()
            if any(denied in f_str for denied in ["confidential", "counselling", "medical_record", "question_paper"]):
                logger.critical(f"Filter contains reference to denied domain: {f_str}")
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="RESTRICTED_RESOURCE",
                    message="Requested filter references strictly quarantined institutional domains.",
                )

        # 7. Dimension Catalog & Metric-Permission Validation
        allowed_dim_ids = set(metric.get("allowed_dimensions", []))
        for dim in intent.dimensions:
            # 7a. Check existence in global dimension catalog
            resolved_dim = None
            for d in self._registry.get_dimensions():
                if dim == d.get("dimension_id") or dim == d.get("canonical_name") or dim == d.get("id"):
                    resolved_dim = d
                    break

            if not resolved_dim:
                logger.warning(f"Intent validation rejected unknown dimension: {dim}")
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="INVALID_DIMENSION",
                    message=f"Dimension '{dim}' is not recognized in the institutional Semantic Catalog.",
                )

            # 7b. Check that dimension is permitted for this specific metric
            if resolved_dim.get("dimension_id") not in allowed_dim_ids:
                logger.warning(
                    f"Dimension '{dim}' ({resolved_dim.get('dimension_id')}) is not permitted for metric '{intent.metric_id}'"
                )
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="DIMENSION_NOT_PERMITTED",
                    message=f"Dimension '{dim}' is not permitted for metric '{intent.metric_id}'. Allowed dimensions: {sorted(list(allowed_dim_ids))}",
                )

        # 8. Filter Validation (Semantic Grounding + Anti-SQL Defense)
        # 8a. Defense-in-depth: SQL pattern detection
        sql_injection_patterns = [
            "select", "insert", "update", "delete", "drop", "truncate",
            "alter", "--", ";", "/*", "*/", "xp_", "union", "exec",
        ]
        for k, v in intent.filters.items():
            combined = f"{k} {v}".lower()
            for pattern in sql_injection_patterns:
                if f" {pattern} " in f" {combined} " or pattern in combined.split() or pattern in [k.lower(), str(v).lower()]:
                    logger.warning(f"SQL pattern detected in filter: {k}={v}")
                    return IntentValidationResult(
                        is_valid=False,
                        status=IntentValidationStatus.REJECTED,
                        error_code="SQL_SYNTAX_REJECTED",
                        message="Filters must be structured key-values. SQL clauses or mutation keywords are strictly prohibited.",
                    )

        # 8b. Reject raw database table names or schema qualified paths
        for k in intent.filters.keys():
            if "." in k or k.startswith("v_") or k.startswith("tbl_"):
                logger.warning(f"Filter key '{k}' references a raw database table or schema.")
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="FILTER_NOT_PERMITTED",
                    message=f"Filter key '{k}' references a raw database object. Filters must be grounded in the Semantic Layer.",
                )

        # 8c. Validate that each filter key is explicitly permitted for this metric
        allowed_filters = self.get_allowed_filter_keys_for_metric(metric)
        for k in intent.filters.keys():
            if k.lower() not in allowed_filters:
                logger.warning(
                    f"Filter key '{k}' is not permitted for metric '{intent.metric_id}'"
                )
                return IntentValidationResult(
                    is_valid=False,
                    status=IntentValidationStatus.REJECTED,
                    error_code="FILTER_NOT_PERMITTED",
                    message=f"Filter key '{k}' is not permitted for metric '{intent.metric_id}'. Allowed filters/dimensions: {sorted(list(allowed_filters))}",
                )

        return IntentValidationResult(
            is_valid=True,
            status=IntentValidationStatus.VALID,
            message="Intent successfully validated against Phase 4 Semantic Catalog.",
            validated_intent=intent,
        )


# Global validator singleton
_intent_validator: Optional[IntentValidator] = None


def get_intent_validator() -> IntentValidator:
    global _intent_validator
    if _intent_validator is None:
        _intent_validator = IntentValidator()
    return _intent_validator
