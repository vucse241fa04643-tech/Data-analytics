"""
Agent 63 – Authentication & Password Service Unit Tests
Tests Argon2id password verification, JWT issuance, claim structure,
expiration, algorithm allowlists, token revocation, and server-side identity resolution.
"""

from datetime import datetime, timezone, timedelta
import jwt
import pytest

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType, ScopedRoleAssignment
from backend.app.services.authentication import AuthenticationService, get_authentication_service
from backend.app.services.identity_repository import InMemoryIdentityRepository
from backend.app.services.password import PasswordManager, get_password_manager
from backend.app.services.token_revocation import InMemoryTokenRevocationStore


@pytest.fixture
def isolated_auth_components():
    pwd_mgr = get_password_manager()
    repo = InMemoryIdentityRepository()
    revocation = InMemoryTokenRevocationStore()

    # Register test user
    hashed = pwd_mgr.hash_password("ValidPassword123!")
    repo.register_test_user(
        user_id="test-user-id-001",
        username="alice",
        email="alice@vignan.ac.in",
        password_hash=hashed,
        scoped_roles=[
            ScopedRoleAssignment(role="FACULTY", scope_type=ScopeType.COURSE_OFFERING, scope_id="cs101")
        ],
        is_active=True,
    )
    # Register inactive user
    repo.register_test_user(
        user_id="test-user-id-002",
        username="bob_inactive",
        email="bob@vignan.ac.in",
        password_hash=hashed,
        scoped_roles=[ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF)],
        is_active=False,
    )

    auth_svc = AuthenticationService(identity_repo=repo, password_mgr=pwd_mgr, revocation_store=revocation)
    return auth_svc, repo, pwd_mgr, revocation


def test_password_manager_argon2id_hashing_and_verification():
    pwd_mgr = PasswordManager()
    plain = "SuperSecretInstitutionalPassword2026!"
    hashed = pwd_mgr.hash_password(plain)

    assert hashed.startswith("$argon2id$")
    assert plain not in hashed
    assert pwd_mgr.verify_password(plain, hashed) is True
    assert pwd_mgr.verify_password("WrongPassword!", hashed) is False
    assert pwd_mgr.verify_password("", hashed) is False
    assert pwd_mgr.verify_password(plain, "") is False


def test_authenticate_valid_credentials(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")

    assert principal is not None
    assert principal.user_id == "test-user-id-001"
    assert principal.username == "alice"
    assert principal.email == "alice@vignan.ac.in"
    assert principal.is_active is True
    assert "FACULTY" in principal.roles
    assert "attendance.read" in principal.permissions


def test_authenticate_invalid_password_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "WrongPassword!")
    assert principal is None


def test_authenticate_unknown_user_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("nonexistent_user", "AnyPassword123!")
    assert principal is None


def test_authenticate_inactive_user_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    with pytest.raises(AuthenticationError, match="inactive or disabled"):
        auth_svc.authenticate_user("bob_inactive", "ValidPassword123!")


def test_token_issuance_and_claim_structure(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token, expires_in, jti = auth_svc.create_access_token(principal)

    assert isinstance(token, str)
    assert expires_in > 0
    assert isinstance(jti, str)

    # Decode without verification to inspect raw claims
    unverified = jwt.decode(token, options={"verify_signature": False})
    assert unverified["sub"] == "test-user-id-001"
    assert unverified["iss"] == settings.JWT_ISSUER
    assert unverified["aud"] == settings.JWT_AUDIENCE
    assert unverified["jti"] == jti
    assert "exp" in unverified
    assert "iat" in unverified
    assert "nbf" in unverified
    # Architectural requirement: minimal claims only
    assert set(unverified.keys()) == {"sub", "jti", "iat", "nbf", "exp", "iss", "aud"}
    assert "username" not in unverified
    # Sensitive items strictly absent from token
    assert "password" not in unverified
    assert "password_hash" not in unverified
    assert "counselling" not in unverified
    assert "roles" not in unverified
    assert "permissions" not in unverified


def test_verify_valid_token(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token, _, jti = auth_svc.create_access_token(principal)

    claims = auth_svc.verify_access_token(token)
    assert claims["sub"] == "test-user-id-001"
    assert claims["jti"] == jti


def test_expired_token_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    now = datetime.now(timezone.utc) - timedelta(hours=2)
    expired_payload = {
        "sub": "test-user-id-001",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int((now - timedelta(minutes=10)).timestamp()),
        "nbf": int((now - timedelta(minutes=10)).timestamp()),
        "exp": int(now.timestamp()),
        "jti": "expired-jti-001",
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(AuthenticationError, match="expired"):
        auth_svc.verify_access_token(expired_token)


def test_tampered_signature_token_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token, _, _ = auth_svc.create_access_token(principal)

    # Sign with wrong secret (32+ bytes to satisfy RFC 7518)
    tampered_token = jwt.encode(
        jwt.decode(token, options={"verify_signature": False}),
        "attacker-compromised-secret-key-32bytes!",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(AuthenticationError, match="signature"):
        auth_svc.verify_access_token(tampered_token)


def test_invalid_algorithm_none_rejected(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    payload = {
        "sub": "test-user-id-001",
        "username": "alice",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        "jti": "jti-alg-none",
    }
    # Attempt algorithm: none attack
    unsecured = jwt.encode(payload, key="", algorithm="none")

    with pytest.raises(AuthenticationError, match="algorithm|invalid"):
        auth_svc.verify_access_token(unsecured)


def test_token_revocation_and_logout(isolated_auth_components):
    auth_svc, _, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token, _, jti = auth_svc.create_access_token(principal)

    # Verify token works before logout
    assert auth_svc.verify_access_token(token)["jti"] == jti

    # Logout / Revoke
    success = auth_svc.logout_token(token)
    assert success is True

    # Subsequent verification must fail
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_svc.verify_access_token(token)

    # Subsequent principal resolution must fail
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_svc.get_principal_from_token(token)


def test_stale_role_claims_cannot_bypass_server_side_authorization(isolated_auth_components):
    """
    CRITICAL CONSTRAINT: Token claims are NOT treated as authoritative for authorization.
    Principal resolution derives active roles and permissions exclusively from the server-side identity repository.
    """
    auth_svc, repo, _, _ = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token, _, _ = auth_svc.create_access_token(principal)

    # Fabricate a token where attacker adds a fake 'role': 'PRINCIPAL' claim
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["roles"] = ["PRINCIPAL", "SUPERUSER"]
    tampered_token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    # Resolving principal from token must inspect server-side state, ignoring the injected token claim
    resolved = auth_svc.get_principal_from_token(tampered_token)
    assert "PRINCIPAL" not in resolved.roles
    assert "SUPERUSER" not in resolved.roles
    assert "FACULTY" in resolved.roles  # Server-side authoritative role


def test_token_revocation_active_rejection(isolated_auth_components):
    """
    Proves that revoked tokens are strictly rejected while the revocation store is active,
    while non-revoked tokens remain valid.
    """
    auth_svc, _, _, revocation = isolated_auth_components
    principal = auth_svc.authenticate_user("alice", "ValidPassword123!")
    token_1, _, jti_1 = auth_svc.create_access_token(principal)
    token_2, _, jti_2 = auth_svc.create_access_token(principal)

    assert jti_1 != jti_2
    assert revocation.is_revoked(jti_1) is False
    assert revocation.is_revoked(jti_2) is False

    # Revoke token 1 only
    auth_svc.logout_token(token_1)
    assert revocation.is_revoked(jti_1) is True
    assert revocation.is_revoked(jti_2) is False

    # Token 1 must be rejected
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_svc.verify_access_token(token_1)
    with pytest.raises(AuthenticationError, match="revoked"):
        auth_svc.get_principal_from_token(token_1)

    # Token 2 must remain valid
    claims_2 = auth_svc.verify_access_token(token_2)
    assert claims_2["jti"] == jti_2
    principal_2 = auth_svc.get_principal_from_token(token_2)
    assert principal_2.user_id == principal.user_id


def test_production_configuration_rejects_test_fixtures(monkeypatch):
    """
    SECURITY CONSTRAINT: InMemoryIdentityRepository with test fixtures must NEVER
    silently act as a production authentication backend.
    In production mode (or ALLOW_TEST_FIXTURES=False), authentication must fail closed.
    """
    from backend.app.core.config import Settings
    from backend.app.services.identity_repository import (
        UnavailableIdentityRepository,
        get_identity_repository,
        reset_identity_repository,
    )

    # Simulate production settings without database connection
    prod_settings = Settings(
        APP_ENV="production",
        AUTH_ENABLED=True,
        JWT_SECRET="production-cryptographically-secure-key-at-least-32-chars-ok",
        ALLOW_TEST_FIXTURES=False,
    )
    monkeypatch.setattr("backend.app.core.config.settings", prod_settings)
    monkeypatch.setattr("backend.app.services.identity_repository.settings", prod_settings)

    reset_identity_repository()
    prod_repo = get_identity_repository()

    assert isinstance(prod_repo, UnavailableIdentityRepository)

    # Test that fixture users cannot authenticate in production configuration
    auth_svc = AuthenticationService(identity_repo=prod_repo)
    for test_user in ["test_principal", "test_hod_cse", "test_student_1", "alice"]:
        result = auth_svc.authenticate_user(test_user, "InstitutionalSecurePass123!")
        assert result is None, f"Test user {test_user} unexpectedly authenticated in production configuration!"

    reset_identity_repository()


def test_fail_closed_when_identity_repository_unavailable():
    """
    Verifies that when identity repository is unavailable, authentication fails safely.
    """
    from backend.app.services.identity_repository import UnavailableIdentityRepository

    unavailable_repo = UnavailableIdentityRepository()
    auth_svc = AuthenticationService(identity_repo=unavailable_repo)

    # Authentication must safely return None
    assert auth_svc.authenticate_user("any_user", "any_password") is None

    # Dummy principal to forge token
    principal = AuthenticatedPrincipal(
        user_id="fake-id",
        username="fake_user",
        email="fake@test.com",
        is_active=True,
        roles=["PRINCIPAL"],
    )
    token, _, _ = auth_svc.create_access_token(principal)

    # Principal resolution must fail closed with AuthenticationError
    with pytest.raises(AuthenticationError, match="unavailable|no longer exists"):
        auth_svc.get_principal_from_token(token)


def test_jwt_secret_validation_insecure_missing_short():
    """
    Validates that production authentication cannot start with an insecure, default, or missing JWT secret.
    """
    from backend.app.core.config import Settings

    # 1. Missing secret when AUTH_ENABLED=True
    with pytest.raises(ValueError, match="JWT_SECRET is required"):
        Settings(AUTH_ENABLED=True, JWT_SECRET="", APP_ENV="development")

    # 2. Secret shorter than 32 characters
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(AUTH_ENABLED=True, JWT_SECRET="too-short-secret", APP_ENV="development")

    # 3. Insecure placeholder in production
    with pytest.raises(ValueError, match="Insecure default, placeholder, or development JWT_SECRET"):
        Settings(
            APP_ENV="production",
            AUTH_ENABLED=True,
            JWT_SECRET="replace-with-secure-32-byte-secret-for-production",
            ALLOW_TEST_FIXTURES=False,
        )

    # 4. Dev secret in production
    with pytest.raises(ValueError, match="Insecure default, placeholder, or development JWT_SECRET"):
        Settings(
            APP_ENV="production",
            AUTH_ENABLED=True,
            JWT_SECRET="agent63-dev-secret-change-in-production-min32bytes",
            ALLOW_TEST_FIXTURES=False,
        )

    # 5. Prohibit ALLOW_TEST_FIXTURES in production
    with pytest.raises(ValueError, match="ALLOW_TEST_FIXTURES cannot be True in production"):
        Settings(
            APP_ENV="production",
            AUTH_ENABLED=True,
            JWT_SECRET="valid-production-secret-with-plenty-of-entropy-32bytes",
            ALLOW_TEST_FIXTURES=True,
        )

    # 6. Valid configuration in production succeeds
    valid_prod = Settings(
        APP_ENV="production",
        AUTH_ENABLED=True,
        JWT_SECRET="valid-production-secret-with-plenty-of-entropy-32bytes",
        ALLOW_TEST_FIXTURES=False,
    )
    assert valid_prod.JWT_SECRET.startswith("valid-production")


def test_auth_disabled_fails_closed(monkeypatch, isolated_auth_components):
    """
    Verifies that when AUTH_ENABLED is False, authentication attempts fail safely
    and protected principal resolution fails closed.
    """
    from backend.app.core.config import Settings

    disabled_settings = Settings(
        AUTH_ENABLED=False,
        APP_ENV="testing",
    )
    monkeypatch.setattr("backend.app.services.authentication.settings", disabled_settings)

    auth_svc, repo, _, _ = isolated_auth_components

    # Login must fail
    with pytest.raises(AuthenticationError, match="Authentication service is disabled"):
        auth_svc.authenticate_user("alice", "ValidPassword123!")

    # Forged/existing token resolution must fail closed
    with pytest.raises(AuthenticationError, match="Authentication service is disabled"):
        auth_svc.get_principal_from_token("some.bearer.token")

