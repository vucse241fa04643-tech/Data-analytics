"""
Agent 63 – Test Health & Readiness Endpoints
Validates liveness and readiness probes under unconfigured database conditions.
"""

from fastapi.testclient import TestClient


def test_health_liveness_endpoint(client: TestClient):
    """GET /api/v1/health should return ok status without requiring database."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "agent63-backend"
    assert "version" in data
    assert "X-Request-ID" in response.headers


def test_health_readiness_endpoint_unconfigured_db(client: TestClient, monkeypatch):
    """GET /api/v1/health/ready should report degraded state because college database is unconfigured."""
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "COLLEGE_DB_HOST", None)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["service"] == "agent63-backend"

    deps = data["dependencies"]
    assert deps["schema_registry"] == "ready"
    assert deps["college_database"] == "not_configured"
    assert deps["schema_registry_objects"] == 236
    assert deps["database_host"] is None
    assert "groq" in deps


def test_no_credentials_in_health_responses(client: TestClient):
    """Verify no passwords, tokens, or raw credentials leak into health payloads."""
    for path in ["/api/v1/health", "/api/v1/health/ready"]:
        res = client.get(path)
        body = res.text.lower()
        assert "password" not in body
        assert "secret" not in body
        assert "postgres://" not in body
        assert "postgresql://" not in body
