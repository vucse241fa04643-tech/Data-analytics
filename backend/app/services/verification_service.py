"""Agent 63 - Phase 14: Official Report Verification Service
Deterministic verification of analytical results against authoritative institutional reports.

SECURITY INVARIANTS:
1. ZERO LLM calls: pure deterministic value and dimension comparison.
2. Re-authorizes principal against metric and scope before verification.
3. Distinguishes:
   - MATCH: Mathematical concordance on metric, period, scope, and value.
   - MISMATCH: Value disagreement.
   - NOT_COMPARABLE: Incompatible period, scope, metric, or non-scalar representation.
   - NOT_VERIFIED: No authoritative registered report found or insufficient evidence.
4. Never declares "certified", "officially approved", or "accredited" without authoritative approval metadata.
5. Strict read-only institutional data access via quality.kpi_value and knowledge.document.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.schemas.export import (
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
)
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType
from backend.app.services.authorization import (
    AuthorizationService,
    get_authorization_service,
)
from backend.app.services.database import (
    CollegeDatabaseService,
    get_database_service,
)
from backend.app.services.export_artifact_store import (
    ExportArtifact,
    ExportArtifactStore,
    get_export_artifact_store,
)
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)

logger = get_logger("agent63.services.verification")

# Technical floating-point representation normalization tolerance (NOT an institutional tolerance).
# Used strictly to normalize IEEE-754 binary floating-point representation noise
# (such as Python float arithmetic producing 84.50000000000001 instead of 84.5).
# Material differences (such as 84.5 vs 84.6 or 84.5 vs 84.5001) are strictly classified as MISMATCH.
FLOAT_REPRESENTATION_ABS_TOL = 1e-9


def _extract_primary_analytical_value(artifact: ExportArtifact) -> Optional[float]:
    """
    Extracts the primary numeric scalar value from an analytical QueryResult.
    For single KPI results or aggregate metric columns, extracts the representative float.
    Returns None for multi-row or non-scalar result shapes.
    """
    rows = artifact.query_result.rows
    if not rows:
        return None

    # Multi-row tabular results are not comparable against a single scalar benchmark
    if len(rows) > 1:
        return None

    first_row = rows[0]
    # Check for prioritized KPI or single-cell aggregate column names
    for key in ("value", "pct", "percentage", "rate", "avg", "count", "attainment", "total"):
        for col_name, val in first_row.items():
            if key in col_name.lower() and val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue

    # Fallback to first numeric column found in the single row
    for val in first_row.values():
        if isinstance(val, (int, float, Decimal)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                continue

    return None


class VerificationService:
    """Service performing deterministic verification of analytical results against official reports."""

    def __init__(
        self,
        artifact_store: Optional[ExportArtifactStore] = None,
        authorization_service: Optional[AuthorizationService] = None,
        semantic_registry: Optional[SemanticRegistryService] = None,
        database_service: Optional[CollegeDatabaseService] = None,
    ):
        self._artifact_store = artifact_store or get_export_artifact_store()
        self._auth_service = authorization_service or get_authorization_service()
        self._semantic_registry = semantic_registry or get_semantic_registry_service()
        self._db_service = database_service or get_database_service()

        # Test fixtures dictionary: strictly empty in production.
        # Only populated during automated test suites via register_test_benchmark().
        self._test_fixtures: Dict[Tuple[str, str, Optional[str], Optional[str]], Dict[str, Any]] = {}

    def register_test_benchmark(
        self,
        metric_id: str,
        period: str,
        value: float,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        unit: Optional[str] = None,
        document_title: str = "Authoritative Institutional Report",
        document_class: str = "REPORT",
        document_version: str = "1.0",
        approved_by: str = "Registrar / IQAC",
    ) -> None:
        """
        Registers an isolated test benchmark fixture.
        Used strictly in unit/integration testing to verify deterministic comparison logic.
        """
        key = (metric_id, period, scope_type, scope_id)
        self._test_fixtures[key] = {
            "metric_id": metric_id,
            "period": period,
            "value": value,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "unit": unit,
            "document_title": document_title,
            "document_class": document_class,
            "document_version": document_version,
            "approved_by": approved_by,
            "registered_at": datetime.now(timezone.utc),
        }

    # Backward compatibility alias for test suites
    def register_official_benchmark(self, *args, **kwargs) -> None:
        self.register_test_benchmark(*args, **kwargs)

    def verify_result(
        self,
        payload: VerificationRequest,
        principal: AuthenticatedPrincipal,
    ) -> VerificationResult:
        """
        Executes deterministic official report verification for an analytical query result.

        Zero LLM calls. Pure structured comparison.
        """
        # 1. Principal Active Status Check
        if not principal or not principal.is_active:
            raise AuthorizationError(
                message="Authentication required and account must be active.",
                details={"code": "INACTIVE_ACCOUNT"},
            )

        # 2. Retrieve server-side cached analytical artifact
        artifact = self._artifact_store.get_artifact(payload.request_id)
        if not artifact:
            raise ValueError(
                "Analytical result not found or session expired. Please re-run the query."
            )

        # 3. Ownership and Cross-User Isolation
        if artifact.user_id != principal.user_id:
            logger.warning(
                f"Cross-user verification attempt blocked: user '{principal.username}' "
                f"attempted to verify artifact belonging to '{artifact.user_id}'"
            )
            raise AuthorizationError(
                message="Access denied: cannot verify another user's analytical result.",
                details={"code": "CROSS_USER_VERIFICATION_BLOCKED"},
            )

        # 4. Re-Authorize Analytical Metric and Scope
        scope_type_enum = (
            ScopeType(artifact.scope_type) if artifact.scope_type else None
        )
        decision = self._auth_service.authorize_metric(
            principal=principal,
            metric_id=artifact.metric_id,
            requested_scope_type=scope_type_enum,
            requested_scope_id=artifact.scope_id,
        )
        if not decision.allowed:
            raise AuthorizationError(
                message=f"Verification unauthorized: {decision.message}",
                details={"code": decision.reason_code},
            )

        # Student self-scope enforcement
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC"):
            if artifact.scope_type and artifact.scope_type != ScopeType.SELF.value:
                raise AuthorizationError(
                    message="Student accounts are restricted to self-scoped records.",
                    details={"code": "SCOPE_OUT_OF_BOUNDS"},
                )

        # HOD department-scope enforcement
        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC", "DEAN"):
            hod_scopes = principal.get_scopes_for_role("HOD")
            allowed_dept_ids = {sr.scope_id for sr in hod_scopes if sr.scope_id}
            if artifact.scope_type == ScopeType.DEPARTMENT.value and artifact.scope_id:
                if artifact.scope_id not in allowed_dept_ids:
                    raise AuthorizationError(
                        message="HOD scope violation: requested verification does not match assigned department.",
                        details={"code": "SCOPE_OUT_OF_BOUNDS"},
                    )

        # 5. Extract Analytical Metadata
        metric_id = artifact.metric_id
        display_name = artifact.metric_display_name
        rows = artifact.query_result.rows
        analytical_val = _extract_primary_analytical_value(artifact)

        # Resolve time context / period from filters
        filters = artifact.filters or {}
        analytical_period = str(
            filters.get("academic_year")
            or filters.get("term_id")
            or filters.get("year")
            or "2024-2025"
        )

        # 6. Look Up Authoritative Institutional Report
        official_report = self._lookup_authoritative_report(
            metric_id=metric_id,
            period=analytical_period,
            scope_type=artifact.scope_type,
            scope_id=artifact.scope_id,
            document_id=payload.document_id,
        )

        # Check for period mismatch if an official report exists for a different period
        if not official_report:
            mismatched_report, mismatch_type = self._find_potential_mismatch_report(
                metric_id=metric_id,
                analytical_period=analytical_period,
                scope_type=artifact.scope_type,
                scope_id=artifact.scope_id,
            )
            if mismatched_report:
                if mismatch_type == "PERIOD":
                    return VerificationResult(
                        status=VerificationStatus.NOT_COMPARABLE,
                        metric_id=metric_id,
                        metric_display_name=display_name,
                        analytical_value=analytical_val,
                        official_value=mismatched_report["value"],
                        unit=mismatched_report.get("unit"),
                        reporting_period=analytical_period,
                        scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
                        document_reference={
                            "title": mismatched_report["document_title"],
                            "version": mismatched_report["document_version"],
                            "period": mismatched_report["period"],
                        },
                        reason=(
                            f"Reporting period mismatch: analytical result is for '{analytical_period}', "
                            f"while registered official report is for '{mismatched_report['period']}'."
                        ),
                        verified_at=datetime.now(timezone.utc),
                    )
                elif mismatch_type == "SCOPE":
                    return VerificationResult(
                        status=VerificationStatus.NOT_COMPARABLE,
                        metric_id=metric_id,
                        metric_display_name=display_name,
                        analytical_value=analytical_val,
                        official_value=mismatched_report["value"],
                        unit=mismatched_report.get("unit"),
                        reporting_period=analytical_period,
                        scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
                        document_reference={
                            "title": mismatched_report["document_title"],
                            "version": mismatched_report["document_version"],
                        },
                        reason=(
                            f"Organizational scope mismatch: analytical result is scoped to '{artifact.scope_id}', "
                            f"while registered official report is scoped to '{mismatched_report.get('scope_id')}'."
                        ),
                        verified_at=datetime.now(timezone.utc),
                    )

        # 7. Evaluate Evidence Availability
        if not official_report:
            return VerificationResult(
                status=VerificationStatus.NOT_VERIFIED,
                metric_id=metric_id,
                metric_display_name=display_name,
                analytical_value=analytical_val,
                official_value=None,
                reporting_period=analytical_period,
                scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
                document_reference=None,
                reason=(
                    f"No registered authoritative institutional report found for metric '{metric_id}' "
                    f"in period '{analytical_period}'."
                ),
                verified_at=datetime.now(timezone.utc),
            )

        # 8. Deterministic Comparison
        official_val = official_report["value"]
        unit = official_report.get("unit")
        doc_ref = {
            "title": official_report["document_title"],
            "class": official_report["document_class"],
            "version": official_report["document_version"],
            "approved_by": official_report["approved_by"],
        }

        # Multi-row result sets are not comparable to scalar official report figures
        if len(rows) > 1:
            return VerificationResult(
                status=VerificationStatus.NOT_COMPARABLE,
                metric_id=metric_id,
                metric_display_name=display_name,
                analytical_value=None,
                official_value=official_val,
                unit=unit,
                reporting_period=analytical_period,
                scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
                document_reference=doc_ref,
                reason=(
                    f"Multi-row tabular result ({len(rows)} rows) cannot be deterministically "
                    f"reconciled against a single scalar official figure."
                ),
                verified_at=datetime.now(timezone.utc),
            )

        if analytical_val is None:
            return VerificationResult(
                status=VerificationStatus.NOT_COMPARABLE,
                metric_id=metric_id,
                metric_display_name=display_name,
                analytical_value=None,
                official_value=official_val,
                unit=unit,
                reporting_period=analytical_period,
                scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
                document_reference=doc_ref,
                reason="Analytical query result does not contain a scalar numeric value for comparison.",
                verified_at=datetime.now(timezone.utc),
            )

        # Exact equality check first (handles Decimal and exact numeric representations)
        is_match = False
        if analytical_val == official_val:
            is_match = True
        else:
            # Technical floating-point representation normalization using math.isclose.
            # This normalizes IEEE-754 representation noise (e.g. 84.50000000000001 vs 84.5).
            # This is NOT an institutional tolerance. Material variations are rejected as MISMATCH.
            try:
                if math.isclose(
                    float(analytical_val),
                    float(official_val),
                    rel_tol=1e-9,
                    abs_tol=FLOAT_REPRESENTATION_ABS_TOL,
                ):
                    is_match = True
            except (ValueError, TypeError):
                is_match = False

        if is_match:
            status = VerificationStatus.MATCH
            reason = (
                f"Mathematical concordance: analytical value ({analytical_val}) matches registered "
                f"official benchmark ({official_val}) for period '{analytical_period}'."
            )
        else:
            status = VerificationStatus.MISMATCH
            diff = round(analytical_val - official_val, 4)
            reason = (
                f"Value mismatch: analytical result computed {analytical_val}, but registered "
                f"official report records {official_val} (variance: {diff})."
            )

        return VerificationResult(
            status=status,
            metric_id=metric_id,
            metric_display_name=display_name,
            analytical_value=analytical_val,
            official_value=official_val,
            unit=unit,
            reporting_period=analytical_period,
            scope={"scope_type": artifact.scope_type, "scope_id": artifact.scope_id},
            document_reference=doc_ref,
            reason=reason,
            verified_at=datetime.now(timezone.utc),
        )

    def _lookup_authoritative_report(
        self,
        metric_id: str,
        period: str,
        scope_type: Optional[str],
        scope_id: Optional[str],
        document_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Looks up authoritative benchmark records.
        Queries PostgreSQL quality.kpi_value JOIN quality.kpi_definition if DB is configured,
        or checks test fixtures if running in isolated unit test mode.
        """
        # 1. Check isolated test fixtures (used during unit testing)
        lookup_key = (metric_id, period, scope_type, scope_id)
        if lookup_key in self._test_fixtures:
            return self._test_fixtures[lookup_key]

        if scope_type == "INSTITUTION":
            inst_key = (metric_id, period, "INSTITUTION", None)
            if inst_key in self._test_fixtures:
                return self._test_fixtures[inst_key]

        # 2. Query Authoritative PostgreSQL Database if configured
        if self._db_service and self._db_service.is_configured():
            try:
                # Query quality.kpi_value join quality.kpi_definition
                # Only rows with validated_at IS NOT NULL are treated as officially validated benchmarks.
                sql = """
                    SELECT 
                        kv.value,
                        kd.code AS metric_id,
                        kd.name AS metric_name,
                        kd.unit,
                        kv.scope_type,
                        kv.scope_id,
                        kv.period_start,
                        kv.period_end,
                        kv.validated_at,
                        doc.document_id,
                        doc.title AS document_title,
                        doc.version AS document_version,
                        doc.document_class,
                        doc.sensitivity
                    FROM quality.kpi_value kv
                    JOIN quality.kpi_definition kd ON kv.kpi_definition_id = kd.kpi_definition_id
                    LEFT JOIN quality.evidence_item ei ON ei.period_start = kv.period_start 
                        AND ei.period_end = kv.period_end
                    LEFT JOIN knowledge.document doc ON ei.document_ref = doc.document_id
                    WHERE kd.code = :metric_id
                      AND kv.validated_at IS NOT NULL
                """
                params: Dict[str, Any] = {"metric_id": metric_id}
                if document_id:
                    sql += " AND (doc.document_id = :doc_id OR ei.evidence_item_id = :doc_id)"
                    params["doc_id"] = document_id

                rows = self._db_service.execute_read_only_query(sql, params)
                for r in rows:
                    p_start = str(r.get("period_start", ""))
                    if period in p_start or not period:
                        return {
                            "metric_id": r["metric_id"],
                            "period": period,
                            "value": float(r["value"]),
                            "scope_type": r.get("scope_type"),
                            "scope_id": str(r["scope_id"]) if r.get("scope_id") else None,
                            "unit": r.get("unit"),
                            "document_title": r.get("document_title") or "Authoritative Quality Benchmark",
                            "document_class": r.get("document_class") or "REPORT",
                            "document_version": r.get("document_version") or "1.0",
                            "approved_by": "Quality Assurance Cell (Validated)",
                        }
            except Exception as e:
                logger.warning(f"Authoritative report query failed (falling back to unverified): {e}")

        return None

    def _find_potential_mismatch_report(
        self,
        metric_id: str,
        analytical_period: str,
        scope_type: Optional[str],
        scope_id: Optional[str],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Finds any registered benchmark for the same metric with mismatched period or scope."""
        for (m_id, o_period, s_type, s_id), o_doc in self._test_fixtures.items():
            if m_id == metric_id:
                if s_type == scope_type and o_period != analytical_period:
                    return o_doc, "PERIOD"
                if o_period == analytical_period and s_id != scope_id:
                    return o_doc, "SCOPE"
        return None, None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_singleton_verification_service: Optional[VerificationService] = None


def get_verification_service() -> VerificationService:
    """Dependency provider for VerificationService."""
    global _singleton_verification_service
    if _singleton_verification_service is None:
        _singleton_verification_service = VerificationService()
    return _singleton_verification_service


def reset_verification_service() -> None:
    """Resets singleton instance for test isolation."""
    global _singleton_verification_service
    _singleton_verification_service = None
