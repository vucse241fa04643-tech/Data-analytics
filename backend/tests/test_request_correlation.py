"""
Agent 63 – Test Request Correlation Middleware
Validates that incoming requests receive or preserve safe correlation IDs without header injection.
"""

import uuid
from fastapi.testclient import TestClient


def test_generated_request_id_when_missing(client: TestClient):
    """If no X-Request-ID header is provided, a valid UUIDv4 is generated and attached."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate it is a valid UUID
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


def test_preserves_valid_client_request_id(client: TestClient):
    """If a valid alphanumeric/UUID correlation ID is sent, it is preserved."""
    custom_id = "agent63-trace-12345678"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_replaces_invalid_or_malformed_request_id(client: TestClient):
    """If an invalid, too-short, or injectable correlation ID is sent, a new UUID is substituted."""
    malicious_ids = [
        "short",  # < 8 chars
        "invalid with spaces",
        "drop table students;--",
        "<script>alert(1)</script>",
        "a" * 100,  # > 64 chars
    ]

    for bad_id in malicious_ids:
        response = client.get("/api/v1/health", headers={"X-Request-ID": bad_id})
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id != bad_id
        # Must have been replaced with a valid UUID
        parsed = uuid.UUID(req_id)
        assert str(parsed) == req_id
