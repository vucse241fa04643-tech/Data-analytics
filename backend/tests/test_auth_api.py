"""
Agent 63 – Authentication API Endpoint Tests
Tests /api/v1/auth/login, /api/v1/auth/me, /api/v1/auth/logout,
header spoofing resistance, token revocation, and correlation ID preservation.
"""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def test_login_success_with_valid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    # Ensure sensitive data not returned
    assert "password" not in data
    assert "hash" not in str(data)


def test_login_invalid_password_returns_401():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "IncorrectPassword!"},
    )
    assert response.status_code == 401
    error = response.json().get("error", {})
    assert error.get("code") == "AUTHENTICATION_FAILED"
    assert "Invalid username or password" in error.get("message", "")


def test_login_unknown_username_returns_401_safely():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent_institutional_user", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    error = response.json().get("error", {})
    assert error.get("code") == "AUTHENTICATION_FAILED"
    # Does not disclose whether user exists
    assert "Invalid username or password" in error.get("message", "")


def test_login_inactive_user_returns_401():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_inactive_user", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 401
    error = response.json().get("error", {})
    assert "inactive" in error.get("message", "").lower()


def test_get_me_unauthenticated_returns_401():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    error = response.json().get("error", {})
    assert error.get("code") == "AUTHENTICATION_FAILED"


def test_get_me_authenticated_returns_sanitized_profile():
    # Login as HOD CSE
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "test_hod_cse", "password": "InstitutionalSecurePass123!"},
    )
    token = login_resp.json()["access_token"]

    # Request profile
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "test_hod_cse"
    assert data["email"] == "hod.cse@vignan.ac.in"
    assert "HOD" in data["roles"]
    assert "attendance.read" in data["permissions"]
    assert data["is_active"] is True
    # Zero password hashes or private secrets leaked
    assert "password" not in data
    assert "secret" not in str(data)


def test_logout_revokes_token():
    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "test_faculty_cse", "password": "InstitutionalSecurePass123!"},
    )
    token = login_resp.json()["access_token"]

    # Verify active
    resp_before = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_before.status_code == 200

    # Logout / Revoke
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["revoked"] is True

    # Subsequent access must be rejected with 401
    resp_after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_after.status_code == 401
    assert "revoked" in resp_after.json()["error"]["message"].lower()


def test_client_role_header_injection_is_strictly_ignored():
    """
    CRITICAL SECURITY TEST: A student client attempts to spoof X-Role: PRINCIPAL.
    The server must strictly derive authorization from the server-side principal.
    """
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "test_student_1", "password": "InstitutionalSecurePass123!"},
    )
    token = login_resp.json()["access_token"]

    # Student sends spoofed role headers
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Role": "PRINCIPAL",
            "X-User-Role": "ADMIN",
            "X-Department-ID": "all",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "PRINCIPAL" not in data["roles"]
    assert "ADMIN" not in data["roles"]
    assert data["roles"] == ["STUDENT"]


def test_auth_preserves_request_correlation_id():
    custom_req_id = "agent63-auth-test-correlation-999"
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
        headers={"X-Request-ID": custom_req_id},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_req_id


def test_login_when_auth_disabled_fails_closed(monkeypatch):
    """
    Verifies that when AUTH_ENABLED is False, login endpoint fails safely.
    """
    from backend.app.core.config import Settings

    disabled_settings = Settings(AUTH_ENABLED=False)
    monkeypatch.setattr("backend.app.core.config.settings", disabled_settings)
    monkeypatch.setattr("backend.app.api.v1.auth.settings", disabled_settings)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 401
    assert "disabled" in response.json()["error"]["message"].lower()


def test_protected_endpoints_when_auth_disabled_fail_closed(monkeypatch):
    """
    SECURITY CONSTRAINT: Disabling authentication must NEVER allow unrestricted access.
    Protected endpoints must fail closed.
    """
    from backend.app.core.config import Settings

    disabled_settings = Settings(AUTH_ENABLED=False)
    monkeypatch.setattr("backend.app.core.config.settings", disabled_settings)
    monkeypatch.setattr("backend.app.dependencies.auth.settings", disabled_settings)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer some.bearer.token"},
    )
    assert response.status_code == 401
    assert "disabled or unconfigured" in response.json()["error"]["message"].lower()


def test_production_config_blocks_test_fixture_logins_via_api(monkeypatch):
    """
    CRITICAL SECURITY CONSTRAINT: In production configuration without database,
    test fixture accounts cannot be used to log in.
    """
    from backend.app.core.config import Settings
    from backend.app.services.identity_repository import (
        UnavailableIdentityRepository,
        reset_identity_repository,
        set_identity_repository,
    )
    from backend.app.services.authentication import reset_authentication_service

    # Inject fail-closed repository as would occur in production
    set_identity_repository(UnavailableIdentityRepository())
    reset_authentication_service()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 401
    assert "invalid username or password" in response.json()["error"]["message"].lower()

    # Reset repository back to default test repository
    reset_identity_repository()
    reset_authentication_service()

