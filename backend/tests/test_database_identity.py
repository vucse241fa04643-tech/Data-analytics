"""
Agent 63 – Database Identity Repository & Production Authentication Tests
Verifies DatabaseIdentityRepository, credential retrieval, Argon2id verification,
scoped role/permission resolution, production repository selection, and fail-closed security.
"""

import pytest
import uuid

from backend.app.core.config import Settings
from backend.app.core.errors import AuthenticationError
from backend.app.schemas.principal import ScopeType
from backend.app.services.authentication import AuthenticationService
from backend.app.services.database import college_database_service
from backend.app.services.identity_repository import (
    DatabaseIdentityRepository,
    InMemoryIdentityRepository,
    UnavailableIdentityRepository,
    get_identity_repository,
    reset_identity_repository,
    set_identity_repository,
)


@pytest.fixture
def db_repo():
    """Returns a DatabaseIdentityRepository connected to the local test database."""
    if not college_database_service.is_configured():
        pytest.skip("College database is not configured for live database identity tests.")
    return DatabaseIdentityRepository(college_database_service)


@pytest.fixture
def auth_service_with_db(db_repo):
    """Returns an AuthenticationService backed by DatabaseIdentityRepository."""
    return AuthenticationService(identity_repo=db_repo)


# ==============================================================================
# 1. User Lookup Tests
# ==============================================================================

def test_database_user_lookup_by_username_case_insensitive(db_repo):
    """Verifies user retrieval by username is case-insensitive and returns expected fields."""
    user = db_repo.get_user_by_username("TEST_PRINCIPAL")
    assert user is not None
    assert user["username"] == "test_principal"
    assert user["email"] == "principal@vignan.ac.in"
    assert user["is_active"] is True
    assert "user_id" in user
    assert "password" not in user
    assert "hash" not in str(user).lower()


def test_database_user_lookup_by_id(db_repo):
    """Verifies user lookup by UUID string."""
    user_by_name = db_repo.get_user_by_username("test_principal")
    assert user_by_name is not None

    user_by_id = db_repo.get_user_by_id(user_by_name["user_id"])
    assert user_by_id is not None
    assert user_by_id["user_id"] == user_by_name["user_id"]
    assert user_by_id["username"] == "test_principal"


def test_database_user_lookup_by_email(db_repo):
    """Verifies user lookup by email is case-insensitive."""
    user = db_repo.get_user_by_email("PRINCIPAL@vignan.ac.in")
    assert user is not None
    assert user["username"] == "test_principal"


def test_database_user_lookup_nonexistent_returns_none(db_repo):
    """Verifies unknown users return None safely."""
    assert db_repo.get_user_by_username("nonexistent_user_xyz") is None
    assert db_repo.get_user_by_id(str(uuid.uuid4())) is None
    assert db_repo.get_user_by_email("nobody@nowhere.internal") is None


# ==============================================================================
# 2. Credential & Argon2id Hash Lookup Tests
# ==============================================================================

def test_database_credential_lookup_returns_argon2id_hash(db_repo):
    """Verifies stored credential hash is retrieved as a valid Argon2id hash."""
    user = db_repo.get_user_by_username("test_principal")
    assert user is not None

    cred_hash = db_repo.get_credential_hash(user["user_id"])
    assert cred_hash is not None
    assert cred_hash.startswith("$argon2id$")


def test_database_credential_lookup_unknown_user_returns_none(db_repo):
    """Verifies credential lookup for unknown user_id returns None."""
    random_id = str(uuid.uuid4())
    assert db_repo.get_credential_hash(random_id) is None


# ==============================================================================
# 3. Scoped Roles and Principal Resolution Tests
# ==============================================================================

def test_database_scoped_roles_principal_institution_scope(db_repo):
    """Verifies test_principal has PRINCIPAL role with INSTITUTION scope."""
    user = db_repo.get_user_by_username("test_principal")
    assert user is not None

    scoped_roles = db_repo.get_scoped_roles(user["user_id"])
    assert len(scoped_roles) >= 1
    role_assignment = next((sr for sr in scoped_roles if sr.role == "PRINCIPAL"), None)
    assert role_assignment is not None
    assert role_assignment.scope_type == ScopeType.INSTITUTION
    assert role_assignment.scope_id is None


def test_database_scoped_roles_hod_department_scope(db_repo):
    """Verifies test_hod_cse has HOD role with DEPARTMENT scope matching CSE."""
    user = db_repo.get_user_by_username("test_hod_cse")
    assert user is not None

    scoped_roles = db_repo.get_scoped_roles(user["user_id"])
    assert len(scoped_roles) >= 1
    role_assignment = next((sr for sr in scoped_roles if sr.role == "HOD"), None)
    assert role_assignment is not None
    assert role_assignment.scope_type == ScopeType.DEPARTMENT
    assert role_assignment.scope_id is not None


def test_database_scoped_roles_counsellor_and_student(db_repo):
    """Verifies test_counsellor and test_student_1 have SELF scope."""
    counsellor = db_repo.get_user_by_username("test_counsellor")
    assert counsellor is not None
    c_roles = db_repo.get_scoped_roles(counsellor["user_id"])
    assert any(sr.role == "COUNSELLOR" and sr.scope_type == ScopeType.SELF for sr in c_roles)

    student = db_repo.get_user_by_username("test_student_1")
    assert student is not None
    s_roles = db_repo.get_scoped_roles(student["user_id"])
    assert any(sr.role == "STUDENT" and sr.scope_type == ScopeType.SELF for sr in s_roles)


def test_database_resolve_principal_authoritative_permissions(db_repo):
    """Verifies resolve_principal sets trusted roles and permissions."""
    user = db_repo.get_user_by_username("test_principal")
    assert user is not None

    principal = db_repo.resolve_principal(user["user_id"])
    assert principal is not None
    assert principal.username == "test_principal"
    assert "PRINCIPAL" in principal.roles
    assert principal.has_permission("analytics.read")
    assert principal.has_permission("export.create")


# ==============================================================================
# 4. Authentication Flow Tests
# ==============================================================================

@pytest.mark.parametrize(
    "username,expected_role",
    [
        ("test_principal", "PRINCIPAL"),
        ("test_management", "MANAGEMENT"),
        ("test_hod_cse", "HOD"),
        ("test_counsellor", "COUNSELLOR"),
        ("test_student_1", "STUDENT"),
    ],
)
def test_authentication_success_all_demo_accounts(auth_service_with_db, username, expected_role):
    """Verifies that all 5 demonstration accounts authenticate with correct credentials."""
    principal = auth_service_with_db.authenticate_user(username, "InstitutionalSecurePass123!")
    assert principal is not None
    assert principal.username == username
    assert expected_role in principal.roles
    assert principal.is_active is True


def test_authentication_invalid_password_returns_none(auth_service_with_db):
    """Verifies invalid password fails authentication and returns None."""
    result = auth_service_with_db.authenticate_user("test_principal", "WrongInvalidPassword!999")
    assert result is None


def test_authentication_unknown_user_returns_none(auth_service_with_db):
    """Verifies unknown username fails authentication and returns None."""
    result = auth_service_with_db.authenticate_user("completely_unknown_user", "InstitutionalSecurePass123!")
    assert result is None


def test_authentication_inactive_user_rejected(db_repo, monkeypatch):
    """Verifies inactive user is rejected with AuthenticationError."""
    # Temporarily mock get_user_by_username to return an inactive user
    def mock_inactive_user(username):
        return {
            "user_id": str(uuid.uuid4()),
            "username": "test_disabled_user",
            "email": "disabled@vignan.ac.in",
            "person_id": None,
            "is_active": False,
            "is_service_account": False,
        }

    monkeypatch.setattr(db_repo, "get_user_by_username", mock_inactive_user)
    monkeypatch.setattr(db_repo, "get_credential_hash", lambda uid: "$argon2id$v=19$mockhash")

    auth_svc = AuthenticationService(identity_repo=db_repo)
    # Mock verify password to pass
    monkeypatch.setattr(auth_svc._password_mgr, "verify_password", lambda p, h: True)

    with pytest.raises(AuthenticationError, match="inactive or disabled"):
        auth_svc.authenticate_user("test_disabled_user", "InstitutionalSecurePass123!")


def test_authentication_missing_credential_returns_none(db_repo, monkeypatch):
    """Verifies user with missing credentials fails closed."""
    def mock_user(username):
        return {
            "user_id": str(uuid.uuid4()),
            "username": "user_no_password",
            "email": "nopass@vignan.ac.in",
            "person_id": None,
            "is_active": True,
            "is_service_account": False,
        }

    monkeypatch.setattr(db_repo, "get_user_by_username", mock_user)
    monkeypatch.setattr(db_repo, "get_credential_hash", lambda uid: None)

    auth_svc = AuthenticationService(identity_repo=db_repo)
    result = auth_svc.authenticate_user("user_no_password", "SomePass123!")
    assert result is None


# ==============================================================================
# 5. Production Repository Selection & Fail-Closed Security Tests
# ==============================================================================

def test_production_repository_selection_with_configured_database(monkeypatch):
    """Verifies that in production with configured database, DatabaseIdentityRepository is chosen."""
    prod_settings = Settings(
        APP_ENV="production",
        ALLOW_TEST_FIXTURES=False,
        JWT_SECRET="production-cryptographically-secure-key-at-least-32-chars-ok",
    )
    monkeypatch.setattr("backend.app.core.config.settings", prod_settings)
    monkeypatch.setattr("backend.app.services.identity_repository.settings", prod_settings)

    reset_identity_repository()
    repo = get_identity_repository()
    assert isinstance(repo, DatabaseIdentityRepository)
    reset_identity_repository()


def test_production_repository_selection_unconfigured_fails_closed(monkeypatch):
    """Verifies that in production with unconfigured database, UnavailableIdentityRepository is chosen."""
    prod_settings = Settings(
        APP_ENV="production",
        ALLOW_TEST_FIXTURES=False,
        JWT_SECRET="production-cryptographically-secure-key-at-least-32-chars-ok",
        COLLEGE_DB_HOST="",
    )
    monkeypatch.setattr("backend.app.core.config.settings", prod_settings)
    monkeypatch.setattr("backend.app.services.identity_repository.settings", prod_settings)

    reset_identity_repository()
    repo = get_identity_repository()
    assert isinstance(repo, UnavailableIdentityRepository)
    assert repo.get_credential_hash(str(uuid.uuid4())) is None
    reset_identity_repository()


def test_development_fallback_to_in_memory_fixtures(monkeypatch):
    """Verifies that in development with ALLOW_TEST_FIXTURES=True, InMemoryIdentityRepository works."""
    dev_settings = Settings(
        APP_ENV="development",
        ALLOW_TEST_FIXTURES=True,
    )
    monkeypatch.setattr("backend.app.core.config.settings", dev_settings)
    monkeypatch.setattr("backend.app.services.identity_repository.settings", dev_settings)

    reset_identity_repository()
    repo = get_identity_repository()
    assert isinstance(repo, InMemoryIdentityRepository)
    # Fixtures are loaded
    assert repo.get_user_by_username("test_principal") is not None
    reset_identity_repository()


def test_no_credential_leakage_in_principal_and_user_representation(db_repo):
    """Verifies that user dictionaries and AuthenticatedPrincipal contain no password hashes."""
    user = db_repo.get_user_by_username("test_principal")
    principal = db_repo.resolve_principal(user["user_id"])

    user_repr = str(user)
    principal_repr = str(principal.model_dump())

    assert "password" not in user_repr.lower()
    assert "argon2" not in user_repr.lower()
    assert "password" not in principal_repr.lower()
    assert "argon2" not in principal_repr.lower()
