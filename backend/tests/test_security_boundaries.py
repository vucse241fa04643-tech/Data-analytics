"""
Agent 63 – Test Security Boundaries & Route Surface Audit
Explicitly asserts the ABSENCE of forbidden endpoints and dangerous abstractions:
- NO arbitrary SQL execution endpoint (e.g. /execute-sql, /query, /sql)
- NO public schema discovery endpoint (e.g. /schema)
- NO authentication bypass endpoint
- NO arbitrary execution methods on DatabaseService
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.database import CollegeDatabaseService


def test_no_arbitrary_sql_endpoints(client: TestClient):
    """Verify that no endpoint exists that accepts arbitrary SQL queries or database commands."""
    forbidden_routes = [
        ("POST", "/execute-sql"),
        ("POST", "/api/v1/execute-sql"),
        ("POST", "/api/v1/sql"),
        ("POST", "/api/v1/query"),
        ("POST", "/query"),
        ("GET", "/sql"),
        ("POST", "/api/v1/raw-query"),
        ("POST", "/api/v1/db/execute"),
    ]

    for method, path in forbidden_routes:
        if method == "POST":
            res = client.post(path, json={"sql": "SELECT 1"})
        else:
            res = client.get(path)
        
        # Must return 404 (Not Found)
        assert res.status_code == 404, f"Forbidden route {method} {path} should not exist!"


def test_no_public_schema_discovery_endpoint(client: TestClient):
    """
    Section 22 requirement:
    Public endpoint such as GET /api/v1/schema must NOT be created in Phase 2.
    """
    forbidden_schema_routes = [
        "/api/v1/schema",
        "/api/v1/schemas",
        "/schema",
        "/api/v1/tables",
        "/api/v1/registry",
    ]

    for path in forbidden_schema_routes:
        res = client.get(path)
        assert res.status_code == 404, f"Public schema discovery endpoint {path} must NOT exist!"


def test_no_auth_bypass_or_mock_endpoints(client: TestClient):
    """Verify no mock-login, bypass, or fake auth endpoints exist."""
    forbidden_auth_routes = [
        "/api/v1/bypass",
        "/api/v1/auth/bypass",
        "/api/v1/auth/mock",
        "/api/v1/login",
        "/admin/bypass",
    ]

    for path in forbidden_auth_routes:
        res = client.post(path, json={"user": "admin"})
        assert res.status_code == 404, f"Auth bypass route {path} must NOT exist!"


def test_database_service_has_no_arbitrary_sql_method():
    """Verify CollegeDatabaseService explicitly does not expose arbitrary SQL execution methods."""
    db = CollegeDatabaseService()
    dangerous_method_names = [
        "execute_arbitrary_sql",
        "execute_sql",
        "run_query",
        "raw_query",
        "execute",
        "cursor",
    ]
    for method_name in dangerous_method_names:
        assert not hasattr(db, method_name), f"CollegeDatabaseService must not have method '{method_name}'"
