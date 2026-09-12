"""
Agent 63 – Safe SQL Validator Security Rejection Matrix Tests (Phase 7)
Tests AST-level security enforcement on compiled SQL artifacts using sqlglot.
Validates:
1. Rejection of multiple statements / semicolons
2. Rejection of DDL / DML / mutation operations
3. Rejection of SQL comments (-- or /* */)
4. Rejection of SELECT * (wildcards)
5. Rejection of confidential / non-allowlisted schemas
6. Rejection of unmapped database tables
7. Rejection of arbitrary / unauthorized functions
8. Rejection of missing, negative, or excessive limits
9. Acceptance of valid, compliant institutional SELECT queries
"""

import pytest
from backend.app.core.errors import SQLValidationError
from backend.app.schemas.sql_artifact import SQLArtifact
from backend.app.services.sql_validator import SQLValidator, get_sql_validator


@pytest.fixture
def validator() -> SQLValidator:
    return get_sql_validator()


def make_artifact(sql: str, limit: int = 100) -> SQLArtifact:
    return SQLArtifact(
        sql=sql,
        parameters={},
        metric_id="attendance.percentage",
        tables=["attendance.v_current_attendance"],
        columns=["adjusted_pct"],
        query_type="METRIC_QUERY",
        limit=limit,
    )


# -------------------------------------------------------------------------
# Valid Query Acceptance
# -------------------------------------------------------------------------

def test_validator_accepts_clean_select_query(validator):
    """Clean, single SELECT query with explicit columns and limit is valid."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "LIMIT 100"
    )
    artifact = make_artifact(sql)
    validated = validator.validate_artifact(artifact)
    assert validated.validation_status == "VALID"


# -------------------------------------------------------------------------
# Security Rejections
# -------------------------------------------------------------------------

def test_validator_rejects_sql_comments_double_dash(validator):
    """SQL comments via -- are strictly rejected."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value -- inline comment\n"
        "FROM attendance.v_current_attendance a\n"
        "LIMIT 100"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "comments are strictly prohibited" in str(exc_info.value)


def test_validator_rejects_sql_comments_block(validator):
    """SQL block comments /* ... */ are strictly rejected."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) /* block */ AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "LIMIT 100"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "comments are strictly prohibited" in str(exc_info.value)


def test_validator_rejects_multiple_statements(validator):
    """Chained statements via semicolon are strictly rejected."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) FROM attendance.v_current_attendance a LIMIT 100;\n"
        "SELECT 1 LIMIT 1"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "Multiple SQL statements" in str(exc_info.value) or "one SQL statement" in str(exc_info.value)


def test_validator_rejects_select_star(validator):
    """SELECT * is strictly forbidden."""
    sql = "SELECT * FROM attendance.v_current_attendance a LIMIT 100"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "SELECT * is strictly prohibited" in str(exc_info.value)


def test_validator_rejects_dml_insert(validator):
    """INSERT statements are strictly rejected."""
    sql = "INSERT INTO core.department (code, name) VALUES ('TEST', 'Test Dept')"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "read-only SELECT statements are permitted" in str(exc_info.value)


def test_validator_rejects_dml_delete(validator):
    """DELETE statements are strictly rejected."""
    sql = "DELETE FROM people.student WHERE student_id = '123'"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "read-only SELECT statements are permitted" in str(exc_info.value)


def test_validator_rejects_ddl_drop(validator):
    """DROP statements are strictly rejected."""
    sql = "DROP TABLE core.department"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "read-only SELECT statements are permitted" in str(exc_info.value)


def test_validator_rejects_confidential_schema(validator):
    """Accessing confidential.* schema is strictly quarantined."""
    sql = "SELECT note_id FROM confidential.counselling_notes LIMIT 10"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "restricted or confidential object" in str(exc_info.value) or "not in the institutional allowlist" in str(exc_info.value)


def test_validator_rejects_system_catalog(validator):
    """Querying PostgreSQL system catalogs like pg_shadow or information_schema is forbidden."""
    sql = "SELECT usename FROM pg_shadow LIMIT 10"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "schema-qualified" in str(exc_info.value) or "restricted" in str(exc_info.value)


def test_validator_rejects_unmapped_table(validator):
    """Querying an unknown table not registered in schema registry is rejected."""
    sql = "SELECT foo FROM core.nonexistent_arbitrary_table LIMIT 10"
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "not registered in the Schema Registry" in str(exc_info.value)


def test_validator_rejects_unauthorized_function(validator):
    """Calling arbitrary or dangerous functions like pg_sleep or system is rejected."""
    sql = (
        "SELECT pg_sleep(5), round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "LIMIT 10"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "Function 'pg_sleep' is not permitted" in str(exc_info.value)


def test_validator_rejects_missing_limit(validator):
    """Queries without a LIMIT clause are rejected."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql))
    assert "mandatory LIMIT clause" in str(exc_info.value)


def test_validator_rejects_limit_exceeding_ceiling(validator):
    """Queries requesting a limit above MAX_QUERY_LIMIT (1000) are rejected."""
    sql = (
        "SELECT round(avg(a.adjusted_pct), 2) AS metric_value\n"
        "FROM attendance.v_current_attendance a\n"
        "LIMIT 5000"
    )
    with pytest.raises(SQLValidationError) as exc_info:
        validator.validate_artifact(make_artifact(sql, limit=5000))
    assert "exceeds maximum permitted ceiling" in str(exc_info.value)
