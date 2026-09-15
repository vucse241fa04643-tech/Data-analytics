#!/usr/bin/env python3
"""
Agent 63 – RLS-Compliant Development Seed Loader
================================================

Loads database/seed/development_seed.sql into PostgreSQL while strictly
enforcing and respecting Row-Level Security (RLS) policies and
FORCE ROW LEVEL SECURITY constraints.

Key Security & Determinism Properties:
1. Zero schema tampering: Does NOT modify schema_full.sql or table DDL.
2. Zero privilege bypass: Does NOT disable RLS, alter table ownership,
   or grant BYPASSRLS.
3. RLS context injection:
   - For assessment.internal_mark: Dynamically resolves the assigned faculty
     from academics.faculty_allocation, sets transaction-local app.faculty_id,
     and verifies academics.teaches_offering(course_offering_id) == true.
     Fails closed if no allocation exists or authorization evaluates to false.
   - For attendance.attendance_summary: Sets transaction-local app.role_codes = 'SYSTEM',
     satisfying the institutional policy att_summary_institution.
4. Transaction batching: Batches statements inside transactions for high performance
   and resilience against constrained memory / connection drops on Render Free tier.
5. Full idempotency: Respects ON CONFLICT DO NOTHING for safe re-runs and resumption.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import psycopg
from psycopg.rows import tuple_row


class AuthorizationError(Exception):
    """Raised when RLS context resolution or authorization pre-check fails."""
    pass


@dataclass
class SQLStatement:
    index: int
    section_num: int
    section_title: str
    target_table: Optional[str]
    sql: str
    start_line: int
    end_line: int


def parse_connection_params(db_url: Optional[str] = None) -> str:
    """Resolve database connection string from argument, env, or .env file."""
    if db_url:
        return db_url
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    # Try .env file if in root
    env_file = Path.cwd() / ".env"
    env_vars: Dict[str, str] = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("\"'")

    host = os.environ.get("COLLEGE_DB_HOST") or env_vars.get("COLLEGE_DB_HOST", "localhost")
    port = os.environ.get("COLLEGE_DB_PORT") or env_vars.get("COLLEGE_DB_PORT", "5432")
    dbname = os.environ.get("COLLEGE_DB_NAME") or env_vars.get("COLLEGE_DB_NAME", "agent63_college")
    user = os.environ.get("COLLEGE_DB_USER") or env_vars.get("COLLEGE_DB_USER", "postgres")
    password = os.environ.get("COLLEGE_DB_PASSWORD") or env_vars.get("COLLEGE_DB_PASSWORD", "")
    sslmode = os.environ.get("COLLEGE_DB_SSL_MODE") or env_vars.get("COLLEGE_DB_SSL_MODE", "prefer")

    # If Render or cloud URL exists in env_vars
    if "DATABASE_URL" in env_vars and env_vars["DATABASE_URL"]:
        return env_vars["DATABASE_URL"]

    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode={sslmode}"
    return f"postgresql://{user}@{host}:{port}/{dbname}?sslmode={sslmode}"


def parse_seed_file(seed_path: Path) -> List[SQLStatement]:
    """Parse development_seed.sql into discrete SQL statements with metadata."""
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")

    statements: List[SQLStatement] = []
    current_sec_num = 0
    current_sec_title = "Preamble"
    stmt_lines: List[str] = []
    stmt_start_line = 1
    stmt_idx = 0

    with open(seed_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            stripped = line.strip()

            # Detect section header comment
            m_sec = re.match(r"^--\s+(\d+)\.\s+(.*)", stripped)
            if m_sec:
                sec_num = int(m_sec.group(1))
                if line_num >= 15:  # Skip top preamble header comment bullets
                    current_sec_num = sec_num
                    current_sec_title = m_sec.group(2).strip()

            # Ignore pure comment lines when no statement is accumulating
            if not stmt_lines and (not stripped or stripped.startswith("--")):
                continue

            if not stmt_lines:
                stmt_start_line = line_num

            stmt_lines.append(line)

            # Statement finishes on ';'
            if stripped.endswith(";"):
                raw_sql = "".join(stmt_lines).strip()
                stmt_lines = []

                # Find target table
                m_insert = re.match(r"INSERT\s+INTO\s+([a-zA-Z0-9_.]+)", raw_sql, re.IGNORECASE)
                m_update = re.match(r"UPDATE\s+([a-zA-Z0-9_.]+)", raw_sql, re.IGNORECASE)

                target_table = None
                if m_insert:
                    target_table = m_insert.group(1).lower()
                elif m_update:
                    target_table = m_update.group(1).lower()

                stmt_idx += 1
                statements.append(
                    SQLStatement(
                        index=stmt_idx,
                        section_num=current_sec_num,
                        section_title=current_sec_title,
                        target_table=target_table,
                        sql=raw_sql,
                        start_line=stmt_start_line,
                        end_line=line_num,
                    )
                )

    return statements


def extract_internal_mark_offering_id(sql: str) -> str:
    """Extract course_offering_id from an assessment.internal_mark INSERT statement."""
    # Pattern: INSERT INTO assessment.internal_mark (cols...) VALUES (vals...)
    m = re.search(
        r"INSERT\s+INTO\s+assessment\.internal_mark\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
        sql,
        re.IGNORECASE,
    )
    if not m:
        raise ValueError(f"Failed to parse internal_mark INSERT columns/values: {sql[:100]}")

    cols = [c.strip() for c in m.group(1).split(",")]
    if "course_offering_id" not in cols:
        raise ValueError(f"course_offering_id column not found in internal_mark statement: {cols}")

    offering_col_idx = cols.index("course_offering_id")
    vals_str = m.group(2)
    # Extract string literals in order
    literals = re.findall(r"'([^']+)'", vals_str)
    if len(literals) <= offering_col_idx:
        raise ValueError(f"Could not extract string literal for course_offering_id index {offering_col_idx} in {vals_str}")

    return literals[offering_col_idx]


class SeedLoaderRLS:
    def __init__(self, conn: psycopg.Connection, statements: List[SQLStatement], dry_run: bool = False):
        self.conn = conn
        self.statements = statements
        self.dry_run = dry_run
        self.allocation_cache: Dict[str, str] = {}
        self.verified_offerings: Set[str] = set()

    def load_faculty_allocations(self) -> Dict[str, str]:
        """Load currently active faculty allocations from database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT course_offering_id, faculty_id
                FROM academics.faculty_allocation
                WHERE valid_to IS NULL OR valid_to >= CURRENT_DATE;
            """)
            allocations = {str(row[0]): str(row[1]) for row in cur.fetchall()}
            self.allocation_cache.update(allocations)
            return self.allocation_cache

    def get_faculty_for_offering(self, offering_id: str) -> str:
        """Resolve faculty_id for a given course_offering_id, failing closed if none found."""
        if offering_id in self.allocation_cache:
            return self.allocation_cache[offering_id]

        # Query database directly in case it was freshly inserted in this session
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT faculty_id
                FROM academics.faculty_allocation
                WHERE course_offering_id = %s
                  AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
                LIMIT 1;
            """, (offering_id,))
            row = cur.fetchone()
            if row:
                faculty_id = str(row[0])
                self.allocation_cache[offering_id] = faculty_id
                return faculty_id

        raise AuthorizationError(
            f"Failing closed: No active faculty allocation found in academics.faculty_allocation "
            f"for course_offering_id '{offering_id}'."
        )

    def execute_internal_mark_statement(self, stmt: SQLStatement, cur: psycopg.Cursor) -> None:
        """Execute assessment.internal_mark insert with verified faculty context."""
        offering_id = extract_internal_mark_offering_id(stmt.sql)
        faculty_id = self.get_faculty_for_offering(offering_id)

        # Set transaction-local faculty identity using set_config (safe parameterized execution)
        cur.execute("SELECT set_config('app.faculty_id', %s, true);", (faculty_id,))

        # Verify authorization using schema function
        if offering_id not in self.verified_offerings:
            cur.execute("SELECT academics.teaches_offering(%s);", (offering_id,))
            res = cur.fetchone()
            is_authorized = bool(res[0]) if res else False
            if not is_authorized:
                raise AuthorizationError(
                    f"Failing closed: academics.teaches_offering('{offering_id}') returned FALSE "
                    f"for faculty_id '{faculty_id}'. RLS policy 'internal_mark_faculty' will reject this write."
                )
            self.verified_offerings.add(offering_id)

        if not self.dry_run:
            cur.execute(stmt.sql)

    def execute_attendance_summary_statement(self, stmt: SQLStatement, cur: psycopg.Cursor) -> None:
        """Execute attendance.attendance_summary insert with SYSTEM institutional context."""
        # Policy att_summary_institution: (identity.has_role('PRINCIPAL') OR identity.has_role('SYSTEM'))
        cur.execute("SELECT set_config('app.role_codes', 'SYSTEM', true);")
        if not self.dry_run:
            cur.execute(stmt.sql)

    def execute_section_15(
        self,
        stmts: List[SQLStatement],
        batch_size: int,
        stats: Dict[str, int],
    ) -> None:
        """
        Execute Section 15 with dependency-safe grouped transactions.

        Dependency Graph Analysis:
        - assessment.assessment_type: References core.institution (Sec 1).
        - academics.student_registration: References people.student (Sec 12) & academics.course_offering (Sec 14).
        - attendance.attendance_summary: References people.student (Sec 12), academics.course_offering (Sec 14), & core.term (Sec 5).
        - assessment.internal_mark: References academics.course_offering (Sec 14) & people.student (Sec 12).
        - assessment.course_result: References people.student (Sec 12), curriculum.course_version (Sec 13), core.term (Sec 5), & academics.course_offering (Sec 14).

        None of the Section 15 tables reference each other. Grouping by table and faculty preserves
        full referential integrity while reducing transactions from >6,000 to 75.
        """
        print(f"\n--> Section 15: ACADEMICS & ASSESSMENT (Optimized Grouped RLS Batching)...")

        # Partition statements in Section 15 by table
        type_stmts: List[SQLStatement] = []
        reg_stmts: List[SQLStatement] = []
        att_stmts: List[SQLStatement] = []
        mark_stmts: List[SQLStatement] = []
        res_stmts: List[SQLStatement] = []
        other_stmts: List[SQLStatement] = []

        for s in stmts:
            if s.target_table == "assessment.assessment_type":
                type_stmts.append(s)
            elif s.target_table == "academics.student_registration":
                reg_stmts.append(s)
            elif s.target_table == "attendance.attendance_summary":
                att_stmts.append(s)
            elif s.target_table == "assessment.internal_mark":
                mark_stmts.append(s)
            elif s.target_table == "assessment.course_result":
                res_stmts.append(s)
            else:
                other_stmts.append(s)

        # 1. Assessment Types (4 statements -> 1 transaction)
        if type_stmts:
            if not self.dry_run:
                with self.conn.transaction():
                    with self.conn.cursor() as cur:
                        for s in type_stmts:
                            cur.execute(s.sql)
            stats["transactions_committed"] += 1
            stats["regular_statements"] += len(type_stmts)
            stats["total_statements"] += len(type_stmts)
            print(f"    [assessment_type] Loaded {len(type_stmts)} types in 1 transaction.")

        # 2. Student Registrations (3,520 statements -> batched in chunks of batch_size)
        for i in range(0, len(reg_stmts), batch_size):
            chunk = reg_stmts[i : i + batch_size]
            if not self.dry_run:
                with self.conn.transaction():
                    with self.conn.cursor() as cur:
                        for s in chunk:
                            cur.execute(s.sql)
            stats["transactions_committed"] += 1
            stats["regular_statements"] += len(chunk)
            stats["total_statements"] += len(chunk)
        print(f"    [student_registration] Loaded {len(reg_stmts)} registrations in {max(1, (len(reg_stmts) + batch_size - 1) // batch_size)} transactions.")

        # 3. Attendance Summaries (3,520 statements -> batched with SYSTEM role context once per transaction)
        att_txns = 0
        for i in range(0, len(att_stmts), batch_size):
            chunk = att_stmts[i : i + batch_size]
            if not self.dry_run:
                with self.conn.transaction():
                    with self.conn.cursor() as cur:
                        cur.execute("SELECT set_config('app.role_codes', 'SYSTEM', true);")
                        for s in chunk:
                            cur.execute(s.sql)
            stats["transactions_committed"] += 1
            stats["attendance_summary_statements"] += len(chunk)
            stats["total_statements"] += len(chunk)
            att_txns += 1
        print(f"    [attendance_summary] Loaded {len(att_stmts)} summaries in {att_txns} transactions (SYSTEM role).")

        # 4. Internal Marks (2,805 statements -> grouped by faculty_id, 1 transaction per faculty)
        from collections import defaultdict
        faculty_groups: Dict[str, List[SQLStatement]] = defaultdict(list)
        for s in mark_stmts:
            offering_id = extract_internal_mark_offering_id(s.sql)
            faculty_id = self.get_faculty_for_offering(offering_id)
            faculty_groups[faculty_id].append(s)

        mark_txns = 0
        for faculty_id, f_stmts in faculty_groups.items():
            # In dry-run or live, perform authorization validation
            distinct_offerings = set(extract_internal_mark_offering_id(s.sql) for s in f_stmts)

            with self.conn.transaction():
                with self.conn.cursor() as cur:
                    # Set transaction-local faculty identity once per transaction
                    cur.execute("SELECT set_config('app.faculty_id', %s, true);", (faculty_id,))

                    # Verify authorization for each distinct offering taught by this faculty
                    for off_id in distinct_offerings:
                        if off_id not in self.verified_offerings:
                            cur.execute("SELECT academics.teaches_offering(%s);", (off_id,))
                            res = cur.fetchone()
                            is_auth = bool(res[0]) if res else False
                            if not is_auth:
                                raise AuthorizationError(
                                    f"Failing closed: academics.teaches_offering('{off_id}') returned FALSE "
                                    f"for faculty_id '{faculty_id}'. RLS policy 'internal_mark_faculty' will reject this write."
                                )
                            self.verified_offerings.add(off_id)

                    # Execute all rows for this faculty within the transaction
                    if not self.dry_run:
                        for s in f_stmts:
                            cur.execute(s.sql)

            stats["transactions_committed"] += 1
            stats["internal_mark_statements"] += len(f_stmts)
            stats["total_statements"] += len(f_stmts)
            mark_txns += 1

        print(f"    [internal_mark] Loaded {len(mark_stmts)} marks across {mark_txns} faculty transactions (Verified RLS context).")

        # 5. Course Results (2,805 statements -> batched in chunks of batch_size)
        for i in range(0, len(res_stmts), batch_size):
            chunk = res_stmts[i : i + batch_size]
            if not self.dry_run:
                with self.conn.transaction():
                    with self.conn.cursor() as cur:
                        for s in chunk:
                            cur.execute(s.sql)
            stats["transactions_committed"] += 1
            stats["regular_statements"] += len(chunk)
            stats["total_statements"] += len(chunk)
        print(f"    [course_result] Loaded {len(res_stmts)} results in {max(1, (len(res_stmts) + batch_size - 1) // batch_size)} transactions.")

        # 6. Any other statements in Section 15
        if other_stmts:
            if not self.dry_run:
                with self.conn.transaction():
                    with self.conn.cursor() as cur:
                        for s in other_stmts:
                            cur.execute(s.sql)
            stats["transactions_committed"] += 1
            stats["regular_statements"] += len(other_stmts)
            stats["total_statements"] += len(other_stmts)

    def run(
        self,
        batch_size: int = 500,
        start_section: int = 1,
        target_section: Optional[int] = None,
    ) -> Dict[str, int]:
        """Execute the loading pipeline."""
        start_time = time.time()
        print("=" * 70)
        print(f"Agent 63 – Secure RLS Development Seed Loader")
        print(f"Mode: {'DRY RUN (Validation only)' if self.dry_run else 'LIVE IMPORT'}")
        print(f"Total parsed statements: {len(self.statements)}")
        print(f"Start section: {start_section} | Target section: {target_section or 'All'}")
        print(f"Transaction batch size: {batch_size}")
        print("=" * 70)

        # Initial allocation preload
        self.load_faculty_allocations()
        print(f"[Init] Preloaded {len(self.allocation_cache)} active faculty allocations from database.")

        stats = {
            "total_statements": 0,
            "internal_mark_statements": 0,
            "attendance_summary_statements": 0,
            "regular_statements": 0,
            "sections_processed": 0,
            "transactions_committed": 0,
        }

        # Filter statements by section
        filtered_stmts: List[SQLStatement] = []
        for s in self.statements:
            if s.section_num < start_section:
                continue
            if target_section is not None and s.section_num != target_section:
                continue
            filtered_stmts.append(s)

        if not filtered_stmts:
            print("[Warn] No statements match the requested section filter.")
            return stats

        # Group statements by section number to handle Section 15 with dedicated batching
        from collections import defaultdict
        section_map: Dict[int, List[SQLStatement]] = defaultdict(list)
        section_titles: Dict[int, str] = {}
        section_start_lines: Dict[int, int] = {}
        for s in filtered_stmts:
            section_map[s.section_num].append(s)
            if s.section_num not in section_titles:
                section_titles[s.section_num] = s.section_title
                section_start_lines[s.section_num] = s.start_line

        for sec_num in sorted(section_map.keys()):
            sec_stmts = section_map[sec_num]
            stats["sections_processed"] += 1

            # Dedicated handler for Section 15 (which contains the FORCE RLS tables)
            if sec_num == 15:
                self.execute_section_15(sec_stmts, batch_size, stats)
                continue

            # Standard batching for all other sections
            print(f"\n--> Section {sec_num}: {section_titles[sec_num]} (Starting line {section_start_lines[sec_num]})...")
            for i in range(0, len(sec_stmts), batch_size):
                chunk = sec_stmts[i : i + batch_size]
                if not self.dry_run:
                    with self.conn.transaction():
                        with self.conn.cursor() as cur:
                            for s in chunk:
                                cur.execute(s.sql)
                stats["transactions_committed"] += 1
                stats["regular_statements"] += len(chunk)
                stats["total_statements"] += len(chunk)

            print(f"    Flushed {len(sec_stmts)} statements in {max(1, (len(sec_stmts) + batch_size - 1) // batch_size)} transactions.")

        duration = time.time() - start_time
        print("\n" + "=" * 70)
        print("SEED IMPORT SUMMARY")
        print("=" * 70)
        print(f"Status:                      SUCCESS ({'DRY RUN' if self.dry_run else 'COMMITTED'})")
        print(f"Total statements processed:  {stats['total_statements']}")
        print(f"  - Regular statements:      {stats['regular_statements']}")
        print(f"  - internal_mark rows:      {stats['internal_mark_statements']} (Grouped across {len(self.verified_offerings)} offerings)")
        print(f"  - attendance_summary rows: {stats['attendance_summary_statements']} (Authorized via SYSTEM role)")
        print(f"Total transactions:          {stats['transactions_committed']}")
        print(f"Distinct verified offerings: {len(self.verified_offerings)}")
        print(f"Execution time:              {duration:.2f} seconds")
        print("=" * 70)
        return stats


def main():
    parser = argparse.ArgumentParser(
        description="Agent 63 – RLS-Compliant Development Seed Loader for PostgreSQL"
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=Path("database/seed/development_seed.sql"),
        help="Path to development_seed.sql (default: database/seed/development_seed.sql)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="PostgreSQL connection string (defaults to DATABASE_URL or COLLEGE_DB_* env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate statements and RLS context resolution without committing writes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for non-RLS statements per transaction (default: 500)",
    )
    parser.add_argument(
        "--start-section",
        type=int,
        default=1,
        help="Section number to start execution from (default: 1)",
    )
    parser.add_argument(
        "--section",
        type=int,
        default=None,
        help="Execute only this specific section number",
    )

    args = parser.parse_args()

    conn_str = parse_connection_params(args.db_url)
    # Mask password for console display
    masked_conn = re.sub(r":([^@]+)@", ":*****@", conn_str)
    print(f"[Connecting] Target database: {masked_conn}")

    try:
        statements = parse_seed_file(args.seed_file)
    except Exception as e:
        print(f"[Error] Failed to parse seed file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with psycopg.connect(conn_str, autocommit=True) as conn:
            loader = SeedLoaderRLS(conn, statements, dry_run=args.dry_run)
            loader.run(
                batch_size=args.batch_size,
                start_section=args.start_section,
                target_section=args.section,
            )
    except AuthorizationError as ae:
        print(f"\n[SECURITY / RLS ABORT] Authorization pre-check failed: {ae}", file=sys.stderr)
        sys.exit(2)
    except psycopg.Error as pe:
        print(f"\n[DATABASE ERROR] PostgreSQL error during load: {pe}", file=sys.stderr)
        sys.exit(3)
    except Exception as ex:
        print(f"\n[UNEXPECTED ERROR] Loader aborted: {ex}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
