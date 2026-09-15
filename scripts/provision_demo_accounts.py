#!/usr/bin/env python3
"""
Agent 63 – Demonstration Account Provisioning Script
Idempotently provisions dedicated, database-backed demonstration accounts
in PostgreSQL for production reviewer access under APP_ENV=production and ALLOW_TEST_FIXTURES=False.

SECURITY & ARCHITECTURAL REQUIREMENTS:
- Strict zero-knowledge hygiene: zero plaintext passwords in source code, zero password/hash logging.
- Passwords accepted via DEMO_PASSWORD environment variable or secure interactive prompt.
- Salting and hashing performed using Argon2id (argon2-cffi).
- Resolves roles, departments, faculty, and students dynamically from PostgreSQL.
- Zero hardcoded UUIDs.
- Wraps entire execution in an atomic transaction; fails closed if any institutional record is missing.
- Idempotent: safe to run repeatedly.
"""

from __future__ import annotations

import getpass
import os
import sys
from typing import Any, Dict, Optional
import uuid

import psycopg
from psycopg.rows import dict_row

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.core.config import settings
from backend.app.services.password import get_password_manager


def get_db_connection_params() -> Dict[str, Any]:
    """Resolves database connection parameters from environment or settings."""
    db_url = os.environ.get("DATABASE_URL") or getattr(settings, "DATABASE_URL", None)
    if db_url and db_url.strip():
        # Clean postgresql+psycopg schema prefix if present
        clean_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        return {"conninfo": clean_url}

    if not (settings.COLLEGE_DB_HOST and settings.COLLEGE_DB_NAME and settings.COLLEGE_DB_USER):
        raise RuntimeError(
            "Database connection parameters not configured. "
            "Set DATABASE_URL or COLLEGE_DB_HOST, COLLEGE_DB_NAME, COLLEGE_DB_USER, COLLEGE_DB_PASSWORD."
        )

    params: Dict[str, Any] = {
        "host": settings.COLLEGE_DB_HOST,
        "port": settings.COLLEGE_DB_PORT,
        "dbname": settings.COLLEGE_DB_NAME,
        "user": settings.COLLEGE_DB_USER,
        "password": settings.COLLEGE_DB_PASSWORD,
        "connect_timeout": settings.COLLEGE_DB_CONNECT_TIMEOUT,
    }
    if settings.COLLEGE_DB_SSL_MODE:
        params["sslmode"] = settings.COLLEGE_DB_SSL_MODE
    return params


def get_demo_password() -> str:
    """Retrieves demonstration password securely without storing in source or logging."""
    # 1. Check environment variable
    env_password = os.environ.get("DEMO_PASSWORD")
    if env_password and env_password.strip():
        return env_password.strip()

    # 2. Check interactive prompt if tty is available
    if sys.stdin.isatty():
        prompted = getpass.getpass("Enter password for demonstration accounts: ")
        if prompted and prompted.strip():
            confirm = getpass.getpass("Confirm password: ")
            if prompted != confirm:
                raise ValueError("Passwords do not match.")
            return prompted.strip()

    raise RuntimeError(
        "Demonstration password not provided. "
        "Set the DEMO_PASSWORD environment variable or run interactively in a TTY."
    )


def provision_demonstration_accounts(password: str) -> None:
    """Provisions demonstration accounts into PostgreSQL inside an atomic transaction."""
    conn_params = get_db_connection_params()
    pwd_mgr = get_password_manager()

    print("[*] Generating Argon2id credential hash...")
    password_hash = pwd_mgr.hash_password(password)

    print("[*] Connecting to PostgreSQL database...")
    if "conninfo" in conn_params:
        conn = psycopg.connect(conn_params["conninfo"], row_factory=dict_row)
    else:
        conn = psycopg.connect(**conn_params, row_factory=dict_row)

    with conn:
        with conn.cursor() as cur:
            print("[*] Ensuring identity.auth_credential table exists...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS identity.auth_credential (
                    user_id UUID PRIMARY KEY REFERENCES identity.app_user(user_id) ON DELETE CASCADE,
                    password_hash TEXT NOT NULL,
                    algorithm VARCHAR(32) NOT NULL DEFAULT 'argon2id',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_auth_credential_user_id ON identity.auth_credential(user_id);
            """)

            print("[*] Ensuring required roles exist in identity.role...")
            cur.execute("""
                INSERT INTO identity.role (code, name, description, is_system)
                VALUES
                    ('MANAGEMENT', 'Institutional Management', 'Executive institutional leadership and governing board', false),
                    ('COUNSELLOR', 'Student Counsellor', 'Student academic and pastoral counselling support', false)
                ON CONFLICT (code) DO NOTHING;
            """)

            print("[*] Dynamically resolving role identifiers...")
            cur.execute("""
                SELECT role_id, code
                FROM identity.role
                WHERE code IN ('PRINCIPAL', 'MANAGEMENT', 'HOD', 'COUNSELLOR', 'STUDENT');
            """)
            roles = {row["code"]: row["role_id"] for row in cur.fetchall()}
            required_roles = ["PRINCIPAL", "MANAGEMENT", "HOD", "COUNSELLOR", "STUDENT"]
            for r in required_roles:
                if r not in roles:
                    raise RuntimeError(f"Required role '{r}' could not be resolved from identity.role. Failing closed.")

            print("[*] Dynamically resolving department records...")
            cur.execute("SELECT department_id FROM core.department WHERE code = 'CSE' LIMIT 1;")
            cse_dept_row = cur.fetchone()
            if not cse_dept_row:
                raise RuntimeError("Department 'CSE' could not be resolved from core.department. Failing closed.")
            cse_dept_id = cse_dept_row["department_id"]

            print("[*] Dynamically resolving faculty / person records for HOD...")
            cur.execute("""
                SELECT f.person_id
                FROM people.faculty f
                JOIN core.department d ON f.department_id = d.department_id
                WHERE d.code = 'CSE'
                ORDER BY f.date_of_joining ASC
                LIMIT 1;
            """)
            hod_faculty = cur.fetchone()
            hod_person_id = hod_faculty["person_id"] if hod_faculty else None

            print("[*] Dynamically resolving counsellor mentor person...")
            cur.execute("""
                SELECT f.person_id
                FROM studentlife.mentorship m
                JOIN people.faculty f ON m.mentor_faculty_id = f.faculty_id
                LIMIT 1;
            """)
            counsellor_row = cur.fetchone()
            if not counsellor_row:
                # Fallback to any faculty in CSE
                cur.execute("""
                    SELECT f.person_id
                    FROM people.faculty f
                    JOIN core.department d ON f.department_id = d.department_id
                    WHERE d.code = 'CSE'
                    LIMIT 1;
                """)
                counsellor_row = cur.fetchone()
            if not counsellor_row:
                raise RuntimeError("No faculty record found to link counsellor person. Failing closed.")
            counsellor_person_id = counsellor_row["person_id"]

            print("[*] Dynamically resolving student record...")
            cur.execute("""
                SELECT s.person_id
                FROM people.student s
                WHERE s.status = 'ACTIVE'
                ORDER BY s.register_no ASC
                LIMIT 1;
            """)
            student_row = cur.fetchone()
            if not student_row:
                raise RuntimeError("No active student record found in people.student. Failing closed.")
            student_person_id = student_row["person_id"]

            # Free counsellor person_id from unused dev accounts if attached
            cur.execute("""
                UPDATE identity.app_user
                SET person_id = NULL
                WHERE username = 'dev_hod_cse' AND person_id = %(person_id)s;
            """, {"person_id": counsellor_person_id})

            # Define demonstration accounts specifications matching in-memory RBAC topology
            demo_definitions = [
                {
                    "username": "test_principal",
                    "email": "principal@vignan.ac.in",
                    "person_id": None,
                    "role_code": "PRINCIPAL",
                    "scope_type": "INSTITUTION",
                    "scope_id": None,
                },
                {
                    "username": "test_management",
                    "email": "management@vignan.ac.in",
                    "person_id": None,
                    "role_code": "MANAGEMENT",
                    "scope_type": "INSTITUTION",
                    "scope_id": None,
                },
                {
                    "username": "test_hod_cse",
                    "email": "hod.cse@vignan.ac.in",
                    "person_id": None,
                    "role_code": "HOD",
                    "scope_type": "DEPARTMENT",
                    "scope_id": cse_dept_id,
                },
                {
                    "username": "test_counsellor",
                    "email": "counsellor@vignan.ac.in",
                    "person_id": counsellor_person_id,
                    "role_code": "COUNSELLOR",
                    "scope_type": "SELF",
                    "scope_id": counsellor_person_id,
                },
                {
                    "username": "test_student_1",
                    "email": "student1@vignan.ac.in",
                    "person_id": student_person_id,
                    "role_code": "STUDENT",
                    "scope_type": "SELF",
                    "scope_id": student_person_id,
                },
            ]

            print("[*] Provisioning demonstration accounts in database...")
            for acc in demo_definitions:
                username = acc["username"]
                # 1. Upsert identity.app_user
                cur.execute("""
                    INSERT INTO identity.app_user (username, email, person_id, auth_provider, is_active)
                    VALUES (%(username)s, %(email)s, %(person_id)s, 'LOCAL', true)
                    ON CONFLICT (username) DO UPDATE
                    SET email = EXCLUDED.email,
                        person_id = EXCLUDED.person_id,
                        auth_provider = 'LOCAL',
                        is_active = true
                    RETURNING user_id;
                """, {
                    "username": username,
                    "email": acc["email"],
                    "person_id": acc["person_id"],
                })
                user_id = cur.fetchone()["user_id"]

                # 2. Re-bind scoped role assignment in identity.user_role
                role_id = roles[acc["role_code"]]
                cur.execute("DELETE FROM identity.user_role WHERE user_id = %(user_id)s;", {"user_id": user_id})
                cur.execute("""
                    INSERT INTO identity.user_role (user_id, role_id, scope_type, scope_id, valid_from)
                    VALUES (%(user_id)s, %(role_id)s, %(scope_type)s, %(scope_id)s, CURRENT_DATE);
                """, {
                    "user_id": user_id,
                    "role_id": role_id,
                    "scope_type": acc["scope_type"],
                    "scope_id": acc["scope_id"],
                })

                # 3. Upsert credential hash in identity.auth_credential
                cur.execute("""
                    INSERT INTO identity.auth_credential (user_id, password_hash, algorithm, updated_at)
                    VALUES (%(user_id)s, %(password_hash)s, 'argon2id', CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE
                    SET password_hash = EXCLUDED.password_hash,
                        algorithm = 'argon2id',
                        updated_at = CURRENT_TIMESTAMP;
                """, {
                    "user_id": user_id,
                    "password_hash": password_hash,
                })

                print(f"    [+] Provisioned '{username}' (Role: {acc['role_code']}, Scope: {acc['scope_type']})")

    print("[SUCCESS] All demonstration accounts provisioned successfully in PostgreSQL.")


if __name__ == "__main__":
    try:
        pw = get_demo_password()
        provision_demonstration_accounts(pw)
    except Exception as exc:
        print(f"[ERROR] Provisioning failed: {exc}", file=sys.stderr)
        sys.exit(1)
