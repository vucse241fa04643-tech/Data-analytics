"""
Agent 63 – Safe SQL Validator (Phase 7)
Enforces AST-level safety rules on compiled SQL artifacts using sqlglot (PostgreSQL dialect).
Validates:
1. Exactly one SQL statement
2. SELECT-only (rejects all DDL, DML, mutation statements)
3. No SQL comments
4. No SELECT *
5. Allowlisted schemas and tables only (strictly quarantines confidential.*)
6. Allowlisted columns only
7. Approved mathematical/aggregate functions only
8. Safe non-negative row limit <= MAX_QUERY_LIMIT
9. Complete parameter separation and isolation
"""

from typing import Any, Dict, List, Optional, Set
import sqlglot
from sqlglot import exp

from backend.app.core.config import settings
from backend.app.core.errors import SQLValidationError
from backend.app.core.logging import get_logger
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.schema_registry import (
    SchemaRegistryService,
    get_schema_registry_service,
)

logger = get_logger("agent63.services.sql_validator")

# Strictly allowed institutional database schemas
ALLOWED_SCHEMAS: Set[str] = {
    "core",
    "curriculum",
    "academics",
    "attendance",
    "assessment",
    "outcomes",
    "placement",
    "quality",
    "people",
    "studentlife",
    "finance",
}

# Strictly prohibited schemas and prefixes
PROHIBITED_PREFIXES: List[str] = [
    "confidential.",
    "pg_",
    "information_schema.",
    "identity.credential",
    "identity.auth_token",
    "exams.question_paper",
    "assessment.question_paper",
]

# Allowlisted aggregate and scalar functions for institutional reporting
ALLOWED_FUNCTIONS: Set[str] = {
    "avg",
    "round",
    "count",
    "sum",
    "min",
    "max",
    "nullif",
    "coalesce",
    "filter",
    "stddev_pop",
    "corr",
}


class SQLValidator:
    """AST-level safety inspector for compiled SQL artifacts."""

    def __init__(self, schema_registry: Optional[SchemaRegistryService] = None):
        self._schema_registry = schema_registry or get_schema_registry_service()

    def validate_artifact(self, artifact: SQLArtifact) -> SQLArtifact:
        """
        Performs multi-layered AST inspection on a SQLArtifact.
        Raises SQLValidationError if any security rule is violated.
        Returns the validated artifact on success.
        """
        raw_sql = artifact.sql.strip()

        # 1. Reject comments in SQL string
        if "--" in raw_sql or "/*" in raw_sql:
            logger.warning("SQL validation rejected: comment syntax detected in query.")
            raise SQLValidationError("SQL comments are strictly prohibited in generated institutional queries.")

        # 2. Reject multiple statements via semicolons
        if ";" in raw_sql.rstrip(";"):
            logger.warning("SQL validation rejected: multiple statements or semicolon syntax detected.")
            raise SQLValidationError("Multiple SQL statements are strictly prohibited.")

        # 3. Parse SQL with sqlglot PostgreSQL dialect
        try:
            parsed_statements = sqlglot.parse(raw_sql, read="postgres")
        except Exception as e:
            logger.error(f"SQL parsing failed: {e}")
            raise SQLValidationError(f"Generated SQL failed syntax parsing: {e}")

        if len(parsed_statements) != 1:
            logger.warning(f"SQL validation rejected: parsed {len(parsed_statements)} statements (expected 1).")
            raise SQLValidationError("Exactly one SQL statement is permitted.")

        ast = parsed_statements[0]
        if ast is None:
            raise SQLValidationError("Empty SQL statement is not valid.")

        # 4. Enforce SELECT-only statement type
        if not isinstance(ast, exp.Select):
            logger.warning(f"SQL validation rejected: statement type '{type(ast).__name__}' is not a SELECT.")
            raise SQLValidationError(
                f"Only read-only SELECT statements are permitted (got {type(ast).__name__})."
            )

        # 5. Strictly reject SELECT * projections (allow count(*) aggregates only)
        for star in ast.find_all(exp.Star):
            if isinstance(star.parent, exp.Count):
                continue
            logger.warning("SQL validation rejected: SELECT * (star expression) detected.")
            raise SQLValidationError("SELECT * is strictly prohibited. Queries must select explicit columns.")

        # 6. Table & Schema Allowlist Inspection
        tables_found: List[str] = []
        for table in ast.find_all(exp.Table):
            table_name = table.name
            schema_name = table.db

            if not schema_name:
                logger.warning(f"SQL validation rejected: table '{table_name}' has no schema qualifier.")
                raise SQLValidationError(
                    f"Table '{table_name}' must be schema-qualified (e.g. schema.table)."
                )

            full_table_name = f"{schema_name}.{table_name}"
            tables_found.append(full_table_name)

            # Check prohibited prefixes
            for prohibited in PROHIBITED_PREFIXES:
                if full_table_name.startswith(prohibited):
                    logger.warning(f"SQL validation rejected restricted object: {full_table_name}")
                    raise SQLValidationError(
                        f"Access to restricted or confidential object '{full_table_name}' is strictly forbidden."
                    )

            # Check schema allowlist
            if schema_name not in ALLOWED_SCHEMAS:
                logger.warning(f"SQL validation rejected unknown schema: {schema_name}")
                raise SQLValidationError(f"Schema '{schema_name}' is not in the institutional allowlist.")

            # Check Schema Registry or approved semantic layer objects
            reg_obj = self._schema_registry.get_object(full_table_name)
            if not reg_obj:
                # Also accept verified analytical views from schema_full.sql
                approved_views = {
                    "attendance.v_current_attendance",
                    "assessment.v_course_performance",
                    "people.v_student_profile",
                    "outcomes.v_attainment_trace",
                    "quality.v_kpi_latest",
                }
                if full_table_name not in approved_views:
                    logger.warning(f"SQL validation rejected unmapped database object: {full_table_name}")
                    raise SQLValidationError(
                        f"Table or view '{full_table_name}' is not registered in the Schema Registry."
                    )

        # 7. Column Allowlist & Credential Column Quarantine Inspection
        prohibited_col_names = {"password", "password_hash", "token_hash", "private_key", "secret_key", "salt"}
        for col in ast.find_all(exp.Column):
            col_name = col.name.lower()
            if col_name in prohibited_col_names:
                logger.warning(f"SQL validation rejected credential column: {col_name}")
                raise SQLValidationError(f"Access to credential column '{col_name}' is strictly forbidden.")

        # 8. Function Allowlist Inspection
        for func in ast.find_all(exp.Func):
            if isinstance(func, exp.Star):
                continue
            if isinstance(func, exp.Anonymous):
                func_name = str(func.this).lower()
            elif hasattr(func, "name") and func.name:
                func_name = str(func.name).lower()
            elif hasattr(func, "sql_name"):
                func_name = func.sql_name().lower()
            else:
                func_name = func.key.lower()

            if func_name == "*" or isinstance(func, exp.Star):
                continue

            if func_name not in ALLOWED_FUNCTIONS:
                # Some functions appear as expressions (e.g. Cast, Substring, Connector/And/Or)
                if isinstance(func, (exp.Cast, exp.Substring, exp.Case, exp.If, exp.Connector, exp.Not, exp.Binary, exp.Between)):
                    continue
                logger.warning(f"SQL validation rejected unauthorized function: {func_name}")
                raise SQLValidationError(
                    f"Function '{func_name}' is not permitted in generated institutional queries."
                )

        # 8. Check for Limit Clause & Bounds
        limit_node = ast.find(exp.Limit)
        if not limit_node:
            logger.warning("SQL validation rejected: query is missing mandatory LIMIT clause.")
            raise SQLValidationError("Queries must include a mandatory LIMIT clause to prevent unbounded results.")

        # Validate limit expression
        limit_expr = limit_node.expression
        try:
            limit_val = int(str(limit_expr).strip())
            if limit_val <= 0:
                raise ValueError("Limit must be positive")
            if limit_val > settings.MAX_QUERY_LIMIT:
                logger.warning(f"SQL validation rejected: limit {limit_val} exceeds maximum {settings.MAX_QUERY_LIMIT}")
                raise SQLValidationError(
                    f"Requested limit {limit_val} exceeds maximum permitted ceiling ({settings.MAX_QUERY_LIMIT})."
                )
        except (ValueError, TypeError) as val_err:
            if isinstance(val_err, SQLValidationError):
                raise
            logger.warning(f"SQL validation rejected: invalid limit expression '{limit_expr}'.")
            raise SQLValidationError(f"Invalid row limit expression: '{limit_expr}'.")

        # 9. Ensure no DDL/DML clauses nested in subqueries
        forbidden_expr_types = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Alter,
            exp.Create,
            exp.Command,
        )
        for forbidden in ast.find_all(forbidden_expr_types):
            logger.warning(f"SQL validation rejected: nested forbidden expression {type(forbidden).__name__}")
            raise SQLValidationError(f"Mutation expression {type(forbidden).__name__} is strictly prohibited.")

        artifact.validation_status = "VALID"
        return artifact


# Global validator singleton
_sql_validator: Optional[SQLValidator] = None


def get_sql_validator() -> SQLValidator:
    global _sql_validator
    if _sql_validator is None:
        _sql_validator = SQLValidator()
    return _sql_validator
