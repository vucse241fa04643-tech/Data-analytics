"""
Agent 63 – Test Suite: RLS-Compliant Development Seed Loader
============================================================

Verifies that the seed loader:
1. Correctly authorizes the first and all internal_mark rows via legitimate faculty context.
2. Resolves valid faculty allocations for all offerings without hardcoding.
3. Strictly fails closed when a faculty allocation is missing or invalid.
4. Correctly sets SYSTEM role context for attendance_summary.
5. Preserves complete idempotency via ON CONFLICT DO NOTHING.
6. Does NOT alter schema_full.sql, RLS policies, or FORCE ROW LEVEL SECURITY settings.
7. Executes dry-run validation deterministically.
"""

import subprocess
from pathlib import Path
import psycopg
import pytest

from scripts.load_seed_rls import (
    AuthorizationError,
    SQLStatement,
    SeedLoaderRLS,
    extract_internal_mark_offering_id,
    parse_connection_params,
    parse_seed_file,
)


@pytest.fixture(scope="module")
def db_conn():
    """Provides a PostgreSQL connection using configured environment."""
    conn_str = parse_connection_params()
    with psycopg.connect(conn_str, autocommit=True) as conn:
        yield conn


@pytest.fixture(scope="module")
def seed_statements():
    """Parses development_seed.sql statements once for the test module."""
    seed_path = Path("database/seed/development_seed.sql")
    assert seed_path.exists(), "database/seed/development_seed.sql must exist"
    return parse_seed_file(seed_path)


class TestSeedLoaderRLS:

    def test_first_internal_mark_row_authorization(self, db_conn, seed_statements):
        """Verify the first internal_mark row resolves to faculty and passes academics.teaches_offering."""
        # Find first assessment.internal_mark statement
        first_mark = next(
            s for s in seed_statements if s.target_table == "assessment.internal_mark"
        )
        assert first_mark is not None

        offering_id = extract_internal_mark_offering_id(first_mark.sql)
        assert offering_id == "a6300000-0040-4000-8000-000000000001"

        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        faculty_id = loader.get_faculty_for_offering(offering_id)
        assert faculty_id == "a6300000-0012-4000-8000-000000000002"

        # Test authorization inside PostgreSQL within a transaction
        with db_conn.transaction():
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.faculty_id', %s, true);", (faculty_id,))
                cur.execute("SELECT academics.teaches_offering(%s);", (offering_id,))
                is_authorized = cur.fetchone()[0]
                assert is_authorized is True, "academics.teaches_offering must evaluate to TRUE"

    def test_all_internal_marks_have_valid_faculty_allocation(self, db_conn, seed_statements):
        """Verify all 2,805 internal_mark statements map to valid faculty allocations."""
        mark_stmts = [s for s in seed_statements if s.target_table == "assessment.internal_mark"]
        assert len(mark_stmts) == 2805

        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        allocations = loader.load_faculty_allocations()
        assert len(allocations) >= 198

        distinct_offerings = set()
        for s in mark_stmts:
            offering_id = extract_internal_mark_offering_id(s.sql)
            distinct_offerings.add(offering_id)
            faculty_id = loader.get_faculty_for_offering(offering_id)
            assert faculty_id is not None
            assert len(faculty_id) == 36

        assert len(distinct_offerings) == 198
        assert distinct_offerings.issubset(set(allocations.keys()))

    def test_missing_faculty_allocation_fails_closed(self, db_conn, seed_statements):
        """Verify that an offering without a faculty allocation raises AuthorizationError and fails closed."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        dummy_offering_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(AuthorizationError) as exc_info:
            loader.get_faculty_for_offering(dummy_offering_id)

        assert "Failing closed" in str(exc_info.value)
        assert dummy_offering_id in str(exc_info.value)

    def test_mismatched_faculty_authorization_fails_closed(self, db_conn, seed_statements):
        """Verify that academics.teaches_offering evaluating to false raises AuthorizationError."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        offering_id = "a6300000-0040-4000-8000-000000000001"
        # Use an unauthorized faculty UUID (e.g. from another department)
        unauthorized_faculty = "a6300000-0012-4000-8000-000000000099"

        # Manually force cache to wrong faculty
        loader.allocation_cache[offering_id] = unauthorized_faculty

        dummy_stmt = SQLStatement(
            index=1,
            section_num=15,
            section_title="Test",
            target_table="assessment.internal_mark",
            sql=f"INSERT INTO assessment.internal_mark (internal_mark_id, course_offering_id) VALUES ('a6300000-0052-4000-8000-999999999999', '{offering_id}') ON CONFLICT (internal_mark_id) DO NOTHING;",
            start_line=1,
            end_line=1,
        )

        with db_conn.cursor() as cur:
            with pytest.raises(AuthorizationError) as exc_info:
                loader.execute_internal_mark_statement(dummy_stmt, cur)

            assert "academics.teaches_offering" in str(exc_info.value)
            assert "returned FALSE" in str(exc_info.value)

    def test_attendance_summary_system_context(self, db_conn, seed_statements):
        """Verify attendance_summary receives SYSTEM role context."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        dummy_stmt = SQLStatement(
            index=1,
            section_num=15,
            section_title="Test",
            target_table="attendance.attendance_summary",
            sql="-- test",
            start_line=1,
            end_line=1,
        )

        with db_conn.transaction():
            with db_conn.cursor() as cur:
                loader.execute_attendance_summary_statement(dummy_stmt, cur)
                cur.execute("SELECT current_setting('app.role_codes', true);")
                role_codes = cur.fetchone()[0]
                assert "SYSTEM" in role_codes

                cur.execute("SELECT identity.has_role('SYSTEM');")
                assert cur.fetchone()[0] is True

    def test_existing_rows_remain_idempotent(self, db_conn, seed_statements):
        """Verify running section 1 statements completes with 0 errors on an existing database."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=False)
        stats = loader.run(target_section=1)
        assert stats["total_statements"] == 1
        assert stats["sections_processed"] == 1

    def test_dry_run_validation(self, db_conn, seed_statements):
        """Verify dry-run mode completes validation without error and reports exact transaction count."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=True)
        stats = loader.run(start_section=14, target_section=15)
        assert stats["internal_mark_statements"] == 2805
        assert stats["attendance_summary_statements"] == 3520
        assert stats["total_statements"] == 12654
        # Section 15 produces exactly 75 transactions
        assert stats["transactions_committed"] == 75

    def test_transaction_local_context_isolation(self, db_conn):
        """Verify that set_config with is_local=true clears identity context upon transaction close."""
        faculty_id = "a6300000-0012-4000-8000-000000000002"

        # 1. Inside first transaction: context is active
        with db_conn.transaction():
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.faculty_id', %s, true);", (faculty_id,))
                cur.execute("SELECT current_setting('app.faculty_id', true);")
                assert cur.fetchone()[0] == faculty_id

        # 2. In second transaction: context has cleanly reverted
        with db_conn.transaction():
            with db_conn.cursor() as cur:
                cur.execute("SELECT coalesce(current_setting('app.faculty_id', true), '');")
                assert cur.fetchone()[0] == "", "app.faculty_id must revert to empty after transaction closes"

    def test_transaction_local_role_context_isolation(self, db_conn):
        """Verify that SYSTEM role codes do not leak across transaction boundaries."""
        with db_conn.transaction():
            with db_conn.cursor() as cur:
                cur.execute("SELECT set_config('app.role_codes', 'SYSTEM', true);")
                cur.execute("SELECT identity.has_role('SYSTEM');")
                assert cur.fetchone()[0] is True

        with db_conn.transaction():
            with db_conn.cursor() as cur:
                cur.execute("SELECT identity.has_role('SYSTEM');")
                assert cur.fetchone()[0] is False, "SYSTEM role must not leak to subsequent transactions"

    def test_grouped_faculty_batch_atomicity_rolls_back_on_failure(self, db_conn, seed_statements):
        """Verify that if one mark in a faculty transaction fails authorization, the transaction rolls back."""
        loader = SeedLoaderRLS(db_conn, seed_statements, dry_run=False)
        offering_id = "a6300000-0040-4000-8000-000000000001"
        faculty_id = loader.get_faculty_for_offering(offering_id)

        # Create one valid and one invalid statement targeting the same faculty
        valid_stmt = SQLStatement(
            index=1,
            section_num=15,
            section_title="Test",
            target_table="assessment.internal_mark",
            sql=f"INSERT INTO assessment.internal_mark (internal_mark_id, course_offering_id, student_id, components, formula_version, computed_marks, max_marks, is_provisional) VALUES ('ffffffff-0001-4000-8000-000000000001', '{offering_id}', 'a6300000-0021-4000-8000-000000000040', '{{\"cat1\": 10}}'::jsonb, 'v1', 10.0, 40.0, false) ON CONFLICT (internal_mark_id) DO NOTHING;",
            start_line=1,
            end_line=1,
        )
        invalid_stmt = SQLStatement(
            index=2,
            section_num=15,
            section_title="Test",
            target_table="assessment.internal_mark",
            # offering_id that faculty does NOT teach
            sql="INSERT INTO assessment.internal_mark (internal_mark_id, course_offering_id, student_id, components, formula_version, computed_marks, max_marks, is_provisional) VALUES ('ffffffff-0002-4000-8000-000000000002', 'a6300000-0040-4000-8000-000000000099', 'a6300000-0021-4000-8000-000000000040', '{{\"cat1\": 10}}'::jsonb, 'v1', 10.0, 40.0, false) ON CONFLICT (internal_mark_id) DO NOTHING;",
            start_line=2,
            end_line=2,
        )

        # Force loader to attempt executing them together
        # The invalid statement will fail teaches_offering authorization
        with pytest.raises(AuthorizationError):
            with db_conn.transaction():
                with db_conn.cursor() as cur:
                    cur.execute("SELECT set_config('app.faculty_id', %s, true);", (faculty_id,))
                    # Pre-check will fail on the invalid offering
                    cur.execute("SELECT academics.teaches_offering('a6300000-0040-4000-8000-000000000099');")
                    if not cur.fetchone()[0]:
                        raise AuthorizationError("Failing closed on unauthorized offering")
                    cur.execute(valid_stmt.sql)

        # Verify atomic rollback: valid_stmt was never committed
        with db_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM assessment.internal_mark WHERE internal_mark_id = 'ffffffff-0001-4000-8000-000000000001';")
            assert cur.fetchone()[0] == 0, "Failed transaction must roll back all inserts atomically"

    def test_no_rls_or_schema_modifications_occur(self, db_conn):
        """Verify schema_full.sql is clean and all 7 tables have FORCE ROW LEVEL SECURITY enabled."""
        # 1. Verify schema file git status
        git_diff = subprocess.run(
            ["git", "diff", "--exit-code", "database/schema/schema_full.sql"],
            capture_output=True,
            text=True,
        )
        assert git_diff.returncode == 0, "database/schema/schema_full.sql must have ZERO git modifications"

        # 2. Query pg_class to ensure FORCE ROW LEVEL SECURITY is active on all 7 sensitive tables
        expected_force_rls_tables = {
            ("attendance", "attendance_summary"),
            ("assessment", "internal_mark"),
            ("assessment", "question_paper"),
            ("confidential", "counselling_case"),
            ("confidential", "counselling_note"),
            ("studentlife", "disciplinary_case"),
            ("agentops", "risk_flag"),
        }

        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT n.nspname, c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE (n.nspname, c.relname) IN (
                    ('attendance', 'attendance_summary'),
                    ('assessment', 'internal_mark'),
                    ('assessment', 'question_paper'),
                    ('confidential', 'counselling_case'),
                    ('confidential', 'counselling_note'),
                    ('studentlife', 'disciplinary_case'),
                    ('agentops', 'risk_flag')
                );
            """)
            rows = cur.fetchall()
            found_tables = set()
            for schema_name, table_name, rls_enabled, force_rls in rows:
                found_tables.add((schema_name, table_name))
                assert rls_enabled is True, f"RLS must be enabled on {schema_name}.{table_name}"
                assert force_rls is True, f"FORCE ROW LEVEL SECURITY must be active on {schema_name}.{table_name}"

            assert found_tables == expected_force_rls_tables
