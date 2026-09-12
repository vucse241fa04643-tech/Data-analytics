"""
Agent 63 – Safe SQL Compiler (Phase 7 Completeness Hardened)
Deterministically compiles validated and authorized StructuredIntent into a read-only,
parameterized PostgreSQL SQLArtifact for ALL approved semantic catalog metrics.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. Zero direct database execution. No PostgreSQL connection is made.
2. Read-only SELECT statements only. DDL/DML is strictly impossible.
3. Strict parameter separation: user filter inputs are never string-interpolated into SQL.
4. Server-side authorization predicate injection based on AuthenticatedPrincipal scope.
   - Distinct aliases per base table (a, cp, cr, im, s, co, ot, cpm, po, prs, qk).
   - STUDENT self-scope strictly enforced where student grain exists; fails closed on institutional capacity metrics.
   - HOD departmental scope strictly enforced; cross-department attempts fail closed.
   - PRINCIPAL and IQAC hold campus-wide scope.
5. Structural AST validation using sqlglot (PostgreSQL dialect) before returning.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.config import settings
from backend.app.core.errors import (
    SQLAuthorizationError,
    SQLCompilationError,
    SQLValidationError,
)
from backend.app.core.logging import get_logger
from backend.app.schemas.intent import (
    IntentType,
    StructuredIntent,
)
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType
from backend.app.schemas.sql_artifact import SQLArtifact, SQLCompilationStatus
from backend.app.services.authorization import (
    AuthorizationService,
    get_authorization_service,
)
from backend.app.services.schema_registry import (
    SchemaRegistryService,
    get_schema_registry_service,
)
from backend.app.services.semantic_registry import (
    SemanticRegistryService,
    get_semantic_registry_service,
)
from backend.app.services.sql_validator import (
    SQLValidator,
    get_sql_validator,
)

logger = get_logger("agent63.services.sql_compiler")

# -------------------------------------------------------------------------
# Base Object Relational Mappings (Authoritative Join Graphs)
# -------------------------------------------------------------------------
BASE_OBJECT_RELATIONS: Dict[str, Dict[str, Any]] = {
    "attendance.v_current_attendance": {
        "alias": "a",
        "student_col": "a.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id "
                "JOIN core.department d ON d.department_id = co.department_id",
                ["academics.course_offering", "core.department"],
                ["course_offering_id", "department_id", "code", "name"],
            ),
            "term": (
                "JOIN core.term t ON t.term_id = a.term_id",
                ["core.term"],
                ["term_id", "label"],
            ),
            "academic_year": (
                "JOIN core.term t ON t.term_id = a.term_id "
                "JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id",
                ["core.term", "core.academic_year"],
                ["term_id", "academic_year_id", "label"],
            ),
            "course": (
                "JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id "
                "JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id",
                ["academics.course_offering", "curriculum.course_version"],
                ["course_offering_id", "course_version_id", "course_code"],
            ),
            "section": (
                "JOIN academics.course_offering co ON co.course_offering_id = a.course_offering_id "
                "JOIN curriculum.section sec ON sec.section_id = co.section_id",
                ["academics.course_offering", "curriculum.section"],
                ["course_offering_id", "section_id", "code"],
            ),
        },
    },
    "assessment.v_course_performance": {
        "alias": "cp",
        "student_col": None,
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN core.department d ON d.department_id = cp.department_id",
                ["core.department"],
                ["department_id", "code", "name"],
            ),
            "term": (
                "JOIN core.term t ON t.term_id = cp.term_id",
                ["core.term"],
                ["term_id", "label"],
            ),
            "academic_year": (
                "JOIN core.term t ON t.term_id = cp.term_id "
                "JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id",
                ["core.term", "core.academic_year"],
                ["term_id", "academic_year_id", "label"],
            ),
            "course": (
                "JOIN curriculum.course_version cv ON cv.course_version_id = cp.course_version_id",
                ["curriculum.course_version"],
                ["course_version_id", "course_code"],
            ),
        },
    },
    "assessment.course_result": {
        "alias": "cr",
        "student_col": "cr.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN academics.course_offering co ON co.course_offering_id = cr.course_offering_id "
                "JOIN core.department d ON d.department_id = co.department_id",
                ["academics.course_offering", "core.department"],
                ["course_offering_id", "department_id", "code", "name"],
            ),
            "term": (
                "JOIN core.term t ON t.term_id = cr.term_id",
                ["core.term"],
                ["term_id", "label"],
            ),
            "academic_year": (
                "JOIN core.term t ON t.term_id = cr.term_id "
                "JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id",
                ["core.term", "core.academic_year"],
                ["term_id", "academic_year_id", "label"],
            ),
            "course": (
                "JOIN curriculum.course_version cv ON cv.course_version_id = cr.course_version_id",
                ["curriculum.course_version"],
                ["course_version_id", "course_code"],
            ),
        },
    },
    "assessment.internal_mark": {
        "alias": "im",
        "student_col": "im.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN academics.course_offering co ON co.course_offering_id = im.course_offering_id "
                "JOIN core.department d ON d.department_id = co.department_id",
                ["academics.course_offering", "core.department"],
                ["course_offering_id", "department_id", "code", "name"],
            ),
            "term": (
                "JOIN academics.course_offering co ON co.course_offering_id = im.course_offering_id "
                "JOIN core.term t ON t.term_id = co.term_id",
                ["academics.course_offering", "core.term"],
                ["course_offering_id", "term_id", "label"],
            ),
            "academic_year": (
                "JOIN academics.course_offering co ON co.course_offering_id = im.course_offering_id "
                "JOIN core.term t ON t.term_id = co.term_id "
                "JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id",
                ["academics.course_offering", "core.term", "core.academic_year"],
                ["course_offering_id", "term_id", "academic_year_id", "label"],
            ),
        },
    },
    "people.student": {
        "alias": "s",
        "student_col": "s.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id "
                "JOIN core.department d ON d.department_id = p.department_id",
                ["curriculum.batch", "curriculum.programme", "core.department"],
                ["batch_id", "programme_id", "department_id", "code", "name"],
            ),
            "programme": (
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id",
                ["curriculum.batch", "curriculum.programme"],
                ["batch_id", "programme_id", "code", "name"],
            ),
            "batch": (
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id",
                ["curriculum.batch"],
                ["batch_id", "label"],
            ),
        },
    },
    "academics.course_offering": {
        "alias": "co",
        "student_col": None,
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN core.department d ON d.department_id = co.department_id",
                ["core.department"],
                ["department_id", "code", "name"],
            ),
            "term": (
                "JOIN core.term t ON t.term_id = co.term_id",
                ["core.term"],
                ["term_id", "label"],
            ),
            "academic_year": (
                "JOIN core.term t ON t.term_id = co.term_id "
                "JOIN core.academic_year ay ON ay.academic_year_id = t.academic_year_id",
                ["core.term", "core.academic_year"],
                ["term_id", "academic_year_id", "label"],
            ),
            "course": (
                "JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id",
                ["curriculum.course_version"],
                ["course_version_id", "course_code"],
            ),
            "section": (
                "JOIN curriculum.section sec ON sec.section_id = co.section_id",
                ["curriculum.section"],
                ["section_id", "code"],
            ),
        },
    },
    "outcomes.v_attainment_trace": {
        "alias": "ot",
        "student_col": None,
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN academics.course_offering co ON co.course_offering_id = ot.course_offering_id "
                "JOIN core.department d ON d.department_id = co.department_id",
                ["academics.course_offering", "core.department"],
                ["course_offering_id", "department_id", "code", "name"],
            ),
            "term": (
                "JOIN core.term t ON t.label = ot.term_label",
                ["core.term"],
                ["term_id", "label"],
            ),
            "course": (
                "JOIN curriculum.course_version cv ON cv.course_code = ot.course_code",
                ["curriculum.course_version"],
                ["course_version_id", "course_code"],
            ),
        },
    },
    "curriculum.co_po_map": {
        "alias": "cpm",
        "student_col": None,
        "dept_join_key": "department",
        "available_joins": {
            "programme": (
                "JOIN curriculum.programme_outcome po ON po.programme_outcome_id = cpm.programme_outcome_id "
                "JOIN curriculum.programme p ON p.programme_id = po.programme_id",
                ["curriculum.programme_outcome", "curriculum.programme"],
                ["programme_outcome_id", "programme_id", "code", "name"],
            ),
            "department": (
                "JOIN curriculum.programme_outcome po ON po.programme_outcome_id = cpm.programme_outcome_id "
                "JOIN curriculum.programme p ON p.programme_id = po.programme_id "
                "JOIN core.department d ON d.department_id = p.department_id",
                ["curriculum.programme_outcome", "curriculum.programme", "core.department"],
                ["programme_outcome_id", "programme_id", "department_id", "code", "name"],
            ),
            "course": (
                "JOIN curriculum.course_outcome co ON co.course_outcome_id = cpm.course_outcome_id "
                "JOIN curriculum.course_version cv ON cv.course_version_id = co.course_version_id",
                ["curriculum.course_outcome", "curriculum.course_version"],
                ["course_outcome_id", "course_version_id", "course_code"],
            ),
        },
    },
    "placement.offer": {
        "alias": "po",
        "student_col": "po.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN people.student s ON s.student_id = po.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id "
                "JOIN core.department d ON d.department_id = p.department_id",
                ["people.student", "curriculum.batch", "curriculum.programme", "core.department"],
                ["student_id", "batch_id", "programme_id", "department_id", "code", "name"],
            ),
            "programme": (
                "JOIN people.student s ON s.student_id = po.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id",
                ["people.student", "curriculum.batch", "curriculum.programme"],
                ["student_id", "batch_id", "programme_id", "code", "name"],
            ),
            "batch": (
                "JOIN people.student s ON s.student_id = po.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id",
                ["people.student", "curriculum.batch"],
                ["student_id", "batch_id", "label"],
            ),
        },
    },
    "placement.readiness_summary": {
        "alias": "prs",
        "student_col": "prs.student_id",
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN people.student s ON s.student_id = prs.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id "
                "JOIN core.department d ON d.department_id = p.department_id",
                ["people.student", "curriculum.batch", "curriculum.programme", "core.department"],
                ["student_id", "batch_id", "programme_id", "department_id", "code", "name"],
            ),
            "programme": (
                "JOIN people.student s ON s.student_id = prs.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id "
                "JOIN curriculum.programme p ON p.programme_id = b.programme_id",
                ["people.student", "curriculum.batch", "curriculum.programme"],
                ["student_id", "batch_id", "programme_id", "code", "name"],
            ),
            "batch": (
                "JOIN people.student s ON s.student_id = prs.student_id "
                "JOIN curriculum.batch b ON b.batch_id = s.batch_id",
                ["people.student", "curriculum.batch"],
                ["student_id", "batch_id", "label"],
            ),
        },
    },
    "quality.v_kpi_latest": {
        "alias": "qk",
        "student_col": None,
        "dept_join_key": "department",
        "available_joins": {
            "department": (
                "JOIN core.department d ON d.department_id = qk.scope_id",
                ["core.department"],
                ["department_id", "code", "name"],
            ),
            "academic_year": (
                "JOIN core.academic_year ay ON qk.period_start >= ay.start_date AND qk.period_end <= ay.end_date",
                ["core.academic_year"],
                ["academic_year_id", "label"],
            ),
        },
    },
}

# -------------------------------------------------------------------------
# Exact Formula Mappings for all 24 Approved Metrics
# -------------------------------------------------------------------------
APPROVED_METRIC_FORMULAS: Dict[str, Dict[str, str]] = {
    "academics.active_student_strength": {
        "formula": "count(DISTINCT s.student_id) FILTER (WHERE s.status = 'ACTIVE')",
        "base_table": "people.student",
    },
    "academics.active_course_offerings": {
        "formula": "count(DISTINCT co.course_offering_id) FILTER (WHERE co.status = 'ACTIVE')",
        "base_table": "academics.course_offering",
    },
    "assessment.course_pass_percentage": {
        "formula": "round(avg(cp.pass_pct), 2)",
        "base_table": "assessment.v_course_performance",
    },
    "assessment.average_total_marks": {
        "formula": "round(avg(cp.avg_total), 2)",
        "base_table": "assessment.v_course_performance",
    },
    "assessment.students_appeared": {
        "formula": "sum(cp.students_appeared)",
        "base_table": "assessment.v_course_performance",
    },
    "assessment.students_passed": {
        "formula": "sum(cp.passed)",
        "base_table": "assessment.v_course_performance",
    },
    "assessment.failure_count": {
        "formula": "count(*) FILTER (WHERE cr.result_status = 'FAIL')",
        "base_table": "assessment.course_result",
    },
    "assessment.internal_marks_average": {
        "formula": "round(avg(im.computed_marks), 2)",
        "base_table": "assessment.internal_mark",
    },
    "attendance.percentage": {
        "formula": "round(avg(a.adjusted_pct), 2)",
        "base_table": "attendance.v_current_attendance",
    },
    "attendance.raw_percentage": {
        "formula": "round(avg(a.raw_pct), 2)",
        "base_table": "attendance.v_current_attendance",
    },
    "attendance.course_aggregate": {
        "formula": "round(avg(a.adjusted_pct), 2)",
        "base_table": "attendance.v_current_attendance",
    },
    "attendance.section_aggregate": {
        "formula": "round(avg(a.adjusted_pct), 2)",
        "base_table": "attendance.v_current_attendance",
    },
    "attendance.shortage_count": {
        "formula": "count(DISTINCT a.student_id) FILTER (WHERE a.band = 'SHORTAGE')",
        "base_table": "attendance.v_current_attendance",
    },
    "outcomes.co_attainment_level": {
        "formula": "round(avg(ot.co_level), 2)",
        "base_table": "outcomes.v_attainment_trace",
    },
    "outcomes.po_attainment_level": {
        "formula": "round(avg(ot.po_level), 2)",
        "base_table": "outcomes.v_attainment_trace",
    },
    "outcomes.co_attaining_percentage": {
        "formula": "round(avg(ot.attaining_pct), 2)",
        "base_table": "outcomes.v_attainment_trace",
    },
    "outcomes.co_po_mapping_strength": {
        "formula": "avg(cpm.strength)",
        "base_table": "curriculum.co_po_map",
    },
    "placement.placed_students_count": {
        "formula": "count(DISTINCT po.student_id) FILTER (WHERE po.status IN ('ACCEPTED', 'JOINED', 'OFFERED'))",
        "base_table": "placement.offer",
    },
    "placement.total_offers_count": {
        "formula": "count(po.offer_id)",
        "base_table": "placement.offer",
    },
    "placement.average_ctc": {
        "formula": "round(avg(po.ctc), 2)",
        "base_table": "placement.offer",
    },
    "placement.highest_ctc": {
        "formula": "max(po.ctc)",
        "base_table": "placement.offer",
    },
    "placement.readiness_average_score": {
        "formula": "round(avg(prs.overall_score), 2)",
        "base_table": "placement.readiness_summary",
    },
    "quality.kpi_latest_value": {
        "formula": "round(avg(qk.value), 2)",
        "base_table": "quality.v_kpi_latest",
    },
    "quality.kpi_target_variance": {
        "formula": "round(avg(qk.variance_pct), 2)",
        "base_table": "quality.v_kpi_latest",
    },
}

# Dimension resolution mapping
DIMENSION_COL_MAP: Dict[str, Dict[str, str]] = {
    "department": {"select": "d.code AS department", "group": "d.code", "join": "department"},
    "dim.department": {"select": "d.code AS department", "group": "d.code", "join": "department"},
    "term": {"select": "t.label AS term", "group": "t.label", "join": "term"},
    "dim.term": {"select": "t.label AS term", "group": "t.label", "join": "term"},
    "academic_year": {"select": "ay.label AS academic_year", "group": "ay.label", "join": "academic_year"},
    "dim.academic_year": {"select": "ay.label AS academic_year", "group": "ay.label", "join": "academic_year"},
    "course": {"select": "cv.course_code AS course", "group": "cv.course_code", "join": "course"},
    "dim.course": {"select": "cv.course_code AS course", "group": "cv.course_code", "join": "course"},
    "batch": {"select": "b.label AS batch", "group": "b.label", "join": "batch"},
    "dim.batch": {"select": "b.label AS batch", "group": "b.label", "join": "batch"},
    "programme": {"select": "p.code AS programme", "group": "p.code", "join": "programme"},
    "dim.programme": {"select": "p.code AS programme", "group": "p.code", "join": "programme"},
    "section": {"select": "sec.code AS section", "group": "sec.code", "join": "section"},
    "dim.section": {"select": "sec.code AS section", "group": "sec.code", "join": "section"},
}


class SQLCompiler:
    """
    Deterministic query compiler translating validated StructuredIntent into
    strictly safe, read-only, parameterized SQLArtifacts.
    """

    def __init__(
        self,
        semantic_registry: Optional[SemanticRegistryService] = None,
        schema_registry: Optional[SchemaRegistryService] = None,
        authorization_service: Optional[AuthorizationService] = None,
        sql_validator: Optional[SQLValidator] = None,
    ):
        self._semantic = semantic_registry or get_semantic_registry_service()
        self._schema = schema_registry or get_schema_registry_service()
        self._authz = authorization_service or get_authorization_service()
        self._validator = sql_validator or get_sql_validator()

    def get_compilation_coverage(self) -> Dict[str, str]:
        """
        Returns coverage status for every metric in the semantic registry.
        Maps metric_id -> 'SUPPORTED' | 'MISSING_SAFE_MAPPING' | 'UNAPPROVED_EXCLUDED'
        """
        report = {}
        all_metrics = self._semantic.load().get("metrics", [])
        for m in all_metrics:
            m_id = m.get("metric_id")
            if not m_id:
                continue
            if m.get("status") != "APPROVED":
                report[m_id] = "UNAPPROVED_EXCLUDED"
            elif m_id in APPROVED_METRIC_FORMULAS:
                report[m_id] = "SUPPORTED"
            else:
                report[m_id] = "MISSING_SAFE_MAPPING"
        return report

    def compile(
        self,
        intent: StructuredIntent,
        principal: AuthenticatedPrincipal,
        request_id: Optional[str] = None,
    ) -> SQLArtifact:
        """
        Compiles a StructuredIntent into an AST-validated SQLArtifact with
        server-side authorization scoping.
        """
        # 1. Reject unsupported or out-of-scope intent types
        if intent.intent_type in (
            IntentType.OUT_OF_SCOPE,
            IntentType.CLARIFICATION_NEEDED,
            IntentType.UNSUPPORTED,
        ):
            raise SQLCompilationError(
                f"Cannot compile SQL for intent type '{intent.intent_type.value}'."
            )

        metric_id = intent.metric_id or intent.primary_metric_id
        if not metric_id:
            raise SQLCompilationError("Structured intent must contain a valid metric_id.")

        # 2. Verify metric definition in Semantic Registry
        metric_def = self._semantic.get_metric(metric_id)
        if not metric_def:
            raise SQLCompilationError(f"Metric '{metric_id}' was not found in semantic catalog.")

        # 3. Server-side authorization check (Verifies status == APPROVED, permissions, sensitivity)
        decision = self._authz.authorize_metric(principal, metric_id)
        if not decision.allowed:
            logger.warning(
                f"Compilation blocked by authorization: principal={principal.username}, "
                f"metric={metric_id}, reason={decision.reason_code}"
            )
            raise SQLAuthorizationError(
                f"Access denied to metric '{metric_id}': {decision.message}"
            )

        # 4. Resolve metric query configuration
        if metric_id not in APPROVED_METRIC_FORMULAS:
            raise SQLCompilationError(
                f"Metric '{metric_id}' genuinely lacks safe deterministic compilation path."
            )

        metric_meta = APPROVED_METRIC_FORMULAS[metric_id]
        base_table = metric_meta["base_table"]
        base_rel = BASE_OBJECT_RELATIONS.get(base_table)
        if not base_rel:
            raise SQLCompilationError(
                f"Base table '{base_table}' for metric '{metric_id}' has no registered relational mappings."
            )

        # 5. Compile query parts
        artifact = self._build_sql_artifact(
            intent=intent,
            metric_def=metric_def,
            base_table=base_table,
            formula=metric_meta["formula"],
            base_rel=base_rel,
            principal=principal,
            request_id=request_id,
        )

        # 6. AST-level safety validation with sqlglot
        validated_artifact = self._validator.validate_artifact(artifact)
        return validated_artifact

    def _build_sql_artifact(
        self,
        intent: StructuredIntent,
        metric_def: Dict[str, Any],
        base_table: str,
        formula: str,
        base_rel: Dict[str, Any],
        principal: AuthenticatedPrincipal,
        request_id: Optional[str] = None,
    ) -> SQLArtifact:
        """Assembles the parameterized SELECT query and extracts metadata."""
        parameters: Dict[str, Any] = {}
        param_counter = 0

        tables_referenced: Set[str] = {base_table}
        columns_referenced: Set[str] = set(metric_def.get("source_columns", []))
        joins_applied: List[str] = []
        applied_join_keys: Set[str] = set()
        filters_applied: List[str] = []
        auth_predicates: List[str] = []
        where_conditions: List[str] = []

        base_alias = base_rel["alias"]
        available_joins = base_rel.get("available_joins", {})

        def require_join(join_key: str):
            """Helper to add join idempotently."""
            if join_key in applied_join_keys:
                return
            if join_key in available_joins:
                join_sql, j_tables, j_cols = available_joins[join_key]
                joins_applied.append(join_sql)
                applied_join_keys.add(join_key)
                for t in j_tables:
                    tables_referenced.add(t)
                for c in j_cols:
                    columns_referenced.add(c)

        # -------------------------------------------------------------
        # 1. Authorization Scoping Predicates (Safe Alias Binding)
        # -------------------------------------------------------------
        # STUDENT Role Scoping
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC"):
            student_col = base_rel.get("student_col")
            if student_col:
                target_id = principal.person_id or principal.user_id
                parameters["auth_student_id"] = target_id
                pred = f"{student_col} = :auth_student_id"
                where_conditions.append(pred)
                auth_predicates.append(pred)
            else:
                # Student cannot query non-student-level institutional capacity metrics
                raise SQLAuthorizationError(
                    "Student accounts are strictly restricted to individual self-scoped records."
                )

        # HOD Role Scoping
        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC", "DEAN", "CAMPUS_ADMIN"):
            hod_scopes = principal.get_scopes_for_role("HOD")
            allowed_dept_ids = {sr.scope_id for sr in hod_scopes if sr.scope_id}
            if not allowed_dept_ids:
                raise SQLAuthorizationError("HOD account has no assigned departmental scope boundary.")

            # Validate requested department against HOD boundary if user specified it
            user_dept = intent.filters.get("department") or intent.filters.get("department_id")
            if user_dept:
                requested_list = user_dept if isinstance(user_dept, list) else [user_dept]
                for req in requested_list:
                    req_clean = str(req).strip().upper()
                    matched = any(
                        req_clean == str(d_id).strip().upper() for d_id in allowed_dept_ids
                    )
                    if not matched:
                        raise SQLAuthorizationError(
                            f"HOD authorization scope violation: department '{req}' is outside assigned scope."
                        )

            # Ensure department join and inject auth predicate
            dept_join_key = base_rel.get("dept_join_key", "department")
            if dept_join_key in available_joins:
                require_join(dept_join_key)
                primary_dept = list(allowed_dept_ids)[0]
                if len(str(primary_dept)) == 36 and "-" in str(primary_dept):
                    parameters["auth_department_id"] = primary_dept
                    pred = "d.department_id = :auth_department_id"
                else:
                    parameters["auth_department_code"] = primary_dept
                    pred = "d.code = :auth_department_code"

                where_conditions.append(pred)
                auth_predicates.append(pred)
            else:
                raise SQLAuthorizationError(
                    f"Metric '{metric_def.get('metric_id')}' does not support departmental scoping."
                )

        # -------------------------------------------------------------
        # 2. Dimensions and Query Structure
        # -------------------------------------------------------------
        select_expressions: List[str] = []
        group_by_expressions: List[str] = []
        order_by_expressions: List[str] = []

        is_aggregate_query = intent.intent_type in (
            IntentType.BREAKDOWN_QUERY,
            IntentType.COMPARISON_QUERY,
            IntentType.TREND_QUERY,
            IntentType.RANKING_QUERY,
        )

        if is_aggregate_query:
            dims = list(intent.dimensions)
            if not dims and intent.intent_type == IntentType.TREND_QUERY:
                dims = ["term"]
            elif not dims and intent.intent_type in (IntentType.BREAKDOWN_QUERY, IntentType.RANKING_QUERY):
                dims = ["department"]

            for dim_name in dims:
                dim_key = dim_name.lower().strip()
                col_info = DIMENSION_COL_MAP.get(dim_key)
                if col_info and col_info["join"] in available_joins:
                    select_expressions.append(col_info["select"])
                    group_by_expressions.append(col_info["group"])
                    require_join(col_info["join"])
                else:
                    logger.debug(f"Dimension '{dim_name}' not available for base table {base_table}")

        # Add the metric formula
        select_expressions.append(f"{formula} AS metric_value")

        # -------------------------------------------------------------
        # 3. User Filters & Parameterization
        # -------------------------------------------------------------
        for f_key, f_val in intent.filters.items():
            if f_key.lower() in ("limit", "order", "sort", "direction"):
                continue

            clean_key = f_key.lower().strip()
            filters_applied.append(clean_key)

            if clean_key in ("department", "dept", "dept_code"):
                if "department" in available_joins:
                    require_join("department")
                    if isinstance(f_val, list):
                        param_placeholders = []
                        for item in f_val:
                            p_name = f"param_{param_counter}"
                            param_counter += 1
                            parameters[p_name] = item
                            param_placeholders.append(f":{p_name}")
                        where_conditions.append(f"d.code IN ({', '.join(param_placeholders)})")
                    else:
                        p_name = f"param_{param_counter}"
                        param_counter += 1
                        parameters[p_name] = f_val
                        where_conditions.append(f"d.code = :{p_name}")

            elif clean_key in ("department_id",):
                if "department" in available_joins:
                    require_join("department")
                    p_name = f"param_{param_counter}"
                    param_counter += 1
                    parameters[p_name] = f_val
                    where_conditions.append(f"d.department_id = :{p_name}")

            elif clean_key in ("term", "term_label"):
                if "term" in available_joins:
                    require_join("term")
                    p_name = f"param_{param_counter}"
                    param_counter += 1
                    parameters[p_name] = f_val
                    where_conditions.append(f"t.label = :{p_name}")

            elif clean_key in ("academic_year", "year"):
                if "academic_year" in available_joins:
                    require_join("academic_year")
                    p_name = f"param_{param_counter}"
                    param_counter += 1
                    parameters[p_name] = f_val
                    where_conditions.append(f"ay.label = :{p_name}")

            elif clean_key in ("course", "course_code"):
                if "course" in available_joins:
                    require_join("course")
                    p_name = f"param_{param_counter}"
                    param_counter += 1
                    parameters[p_name] = f_val
                    where_conditions.append(f"cv.course_code = :{p_name}")

            elif clean_key in ("batch",):
                if "batch" in available_joins:
                    require_join("batch")
                    p_name = f"param_{param_counter}"
                    param_counter += 1
                    parameters[p_name] = f_val
                    where_conditions.append(f"b.label = :{p_name}")

            elif clean_key in ("status",):
                p_name = f"param_{param_counter}"
                param_counter += 1
                parameters[p_name] = f_val
                where_conditions.append(f"{base_alias}.status = :{p_name}")

            elif clean_key in ("band",):
                p_name = f"param_{param_counter}"
                param_counter += 1
                parameters[p_name] = f_val
                where_conditions.append(f"{base_alias}.band = :{p_name}")

        # Process Time Context
        tc = intent.time_context
        if tc.academic_year and "academic_year" not in filters_applied and "year" not in filters_applied:
            if "academic_year" in available_joins:
                require_join("academic_year")
                p_name = f"param_{param_counter}"
                param_counter += 1
                parameters[p_name] = tc.academic_year
                where_conditions.append(f"ay.label = :{p_name}")
                filters_applied.append("academic_year")

        if tc.term and "term" not in filters_applied:
            if "term" in available_joins:
                require_join("term")
                p_name = f"param_{param_counter}"
                param_counter += 1
                parameters[p_name] = tc.term
                where_conditions.append(f"t.label = :{p_name}")
                filters_applied.append("term")

        # -------------------------------------------------------------
        # 4. Order By & Limit Clauses
        # -------------------------------------------------------------
        limit_val = settings.DEFAULT_QUERY_LIMIT
        user_limit = intent.filters.get("limit")
        if user_limit is not None:
            try:
                parsed_limit = int(user_limit)
                if 0 < parsed_limit <= settings.MAX_QUERY_LIMIT:
                    limit_val = parsed_limit
            except (ValueError, TypeError):
                pass
        elif intent.intent_type == IntentType.RANKING_QUERY:
            limit_val = 10

        if intent.intent_type == IntentType.RANKING_QUERY:
            sort_dir = "ASC" if str(intent.filters.get("order", "")).lower() == "asc" else "DESC"
            order_by_expressions.append(f"metric_value {sort_dir}")
        elif intent.intent_type == IntentType.TREND_QUERY:
            if group_by_expressions:
                order_by_expressions.append(f"{group_by_expressions[0]} ASC")
        elif is_aggregate_query:
            order_by_expressions.append("metric_value DESC")

        # -------------------------------------------------------------
        # 5. Assemble SQL Query
        # -------------------------------------------------------------
        sql_lines = [
            f"SELECT {', '.join(select_expressions)}",
            f"FROM {base_table} {base_alias}",
        ]

        if joins_applied:
            for j in joins_applied:
                sql_lines.append(j)

        if where_conditions:
            sql_lines.append(f"WHERE {' AND '.join(where_conditions)}")

        if group_by_expressions:
            sql_lines.append(f"GROUP BY {', '.join(group_by_expressions)}")

        if order_by_expressions:
            sql_lines.append(f"ORDER BY {', '.join(order_by_expressions)}")

        sql_lines.append(f"LIMIT {limit_val}")

        compiled_sql = "\n".join(sql_lines)

        return SQLArtifact(
            sql=compiled_sql,
            parameters=parameters,
            metric_id=metric_def.get("metric_id", ""),
            tables=sorted(list(tables_referenced)),
            columns=sorted(list(columns_referenced)),
            joins=joins_applied,
            filters=filters_applied,
            authorization_predicates=auth_predicates,
            query_type=intent.intent_type.value,
            limit=limit_val,
            read_only=True,
            validation_status="PENDING_VALIDATION",
        )


# Singleton factory pattern
_sql_compiler: Optional[SQLCompiler] = None


def get_sql_compiler() -> SQLCompiler:
    """Provides singleton instance of SQLCompiler."""
    global _sql_compiler
    if _sql_compiler is None:
        _sql_compiler = SQLCompiler()
    return _sql_compiler
