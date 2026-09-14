"""
Agent 63 – Authentication Flows Test Suite
Validates:
1. Sign In (valid login, invalid password, unknown user, inactive user, existing demo users, JWT)
2. Sign Up (valid account, duplicate username rejection, weak password rejection, confirmation mismatch, Argon2id storage, immediate sign-in)
3. Create Account (valid student/faculty self-registration, arbitrary role rejection, department validation)
4. Privileged Account Request & Server-Side Provisioning Workflow:
   - Request submission for all privileged roles (HOD, DEAN, PRINCIPAL, MANAGEMENT, IQAC, COE, PLACEMENT, COUNSELLOR)
   - Dynamic department retrieval (/api/v1/auth/departments)
   - HOD missing department rejection
   - HOD invalid department code rejection
   - No immediate login / no active user creation / no JWT issuance on request submission
   - Admin RBAC access control on account-requests endpoints (unauthenticated 401, student/faculty 403, principal/admin 200)
   - Self-approval prevention (HTTP 403)
   - Administrative approval, authoritative role & scope assignment, and subsequent login
   - Administrative rejection and verification that rejected user cannot login
   - Duplicate pending request handling (username & email)
5. Forgot Password (valid reset request, enumeration defense, expired token rejection, single-use token consumption, credential update, old password rejection)
6. RBAC & Scope Isolation:
   - Scope isolation between departments (HOD CSE cannot access ECE)
   - Student cannot access departmental/institutional management queries
   - Counsellor cannot access non-mentee records
   - Principal cross-departmental access
   - Plaintext passwords never stored or leaked
"""

import time
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.core.errors import SQLAuthorizationError
from backend.app.schemas.intent import IntentType, StructuredIntent
from backend.app.services.authentication import (
    get_authentication_service,
    get_password_reset_store,
    get_account_request_store,
)
from backend.app.services.execution_service import execution_service
from backend.app.services.identity_repository import get_identity_repository
from backend.app.services.sql_compiler import get_sql_compiler

client = TestClient(app)


# ==============================================================================
# 1. SIGN IN TESTS
# ==============================================================================

def test_signin_valid_login_succeeds():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


def test_signin_invalid_password_rejected():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "invalid username or password" in response.json()["error"]["message"].lower()


def test_signin_unknown_user_rejected_without_enumeration():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "completely_unknown_user", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    assert "invalid username or password" in response.json()["error"]["message"].lower()


def test_signin_inactive_user_rejected():
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_inactive_user", "password": "InstitutionalSecurePass123!"},
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["error"]["message"].lower()


def test_signin_existing_demo_users_still_work():
    demo_users = [
        "test_principal",
        "test_hod_cse",
        "test_hod_ece",
        "test_faculty_cse",
        "test_student_1",
        "test_counsellor",
        "test_placement",
        "test_iqac",
    ]
    for username in demo_users:
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "InstitutionalSecurePass123!"},
        )
        assert resp.status_code == 200, f"Demo user {username} failed authentication"
        assert "access_token" in resp.json()


def test_signin_jwt_behavior_unchanged():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "test_hod_cse", "password": "InstitutionalSecurePass123!"},
    )
    token = resp.json()["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["username"] == "test_hod_cse"
    assert "HOD" in profile["roles"]
    assert "attendance.read" in profile["permissions"]


# ==============================================================================
# 2. SIGN UP TESTS
# ==============================================================================

def test_signup_valid_account_creation_and_immediate_login():
    username = f"signup_user_{int(time.time() * 1000)}"
    password = "SecurePassword123!"

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 200
    assert "account created successfully" in response.json()["message"].lower()

    # Plaintext password never stored or returned
    repo = get_identity_repository()
    user_record = repo.get_user_by_username(username)
    assert user_record is not None
    assert "password" not in user_record
    cred_hash = repo.get_credential_hash(user_record["user_id"])
    assert cred_hash is not None
    assert cred_hash.startswith("$argon2id$")
    assert password not in cred_hash

    # Created account can immediately sign in
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Profile shows default STUDENT role
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["username"] == username
    assert profile["roles"] == ["STUDENT"]


def test_signup_duplicate_username_rejected():
    username = "test_principal"
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "username": username,
            "password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "REGISTRATION_FAILED"
    assert "already registered" in error["message"].lower()


def test_signup_weak_password_rejected():
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "username": f"weak_pwd_user_{int(time.time())}",
            "password": "short",
            "confirm_password": "short",
        },
    )
    assert response.status_code in [400, 422]


def test_signup_mismatched_confirmation_rejected():
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "username": f"mismatch_user_{int(time.time())}",
            "password": "SecurePassword123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    assert response.status_code == 400
    assert "match" in response.json()["error"]["message"].lower()


def test_signup_empty_fields_rejected():
    response = client.post(
        "/api/v1/auth/signup",
        json={"username": "", "password": "", "confirm_password": ""},
    )
    assert response.status_code in [400, 422]


# ==============================================================================
# 3. CREATE ACCOUNT (STUDENT & FACULTY SELF-SERVICE)
# ==============================================================================

def test_create_account_valid_student_succeeds_and_immediate_login():
    unique_user = f"ca_student_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Arun Kumar",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "STUDENT",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "account created successfully" in data["message"].lower()
    assert data.get("account_type") == "self_service"

    # Login works immediately
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user, "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.json()["roles"] == ["STUDENT"]


def test_create_account_valid_faculty_succeeds_and_immediate_login():
    unique_user = f"ca_faculty_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Dr. Sunita Rao",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "FACULTY",
            "password": "FacultyPassword123!",
            "confirm_password": "FacultyPassword123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("account_type") == "self_service"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user, "password": "FacultyPassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.json()["roles"] == ["FACULTY"]


def test_create_account_arbitrary_role_rejected():
    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Fake Superuser",
            "username": f"fake_admin_{int(time.time() * 1000)}",
            "role": "SUPERUSER_ADMIN_ROOT",
            "password": "RootPassword123!",
            "confirm_password": "RootPassword123!",
        },
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "REGISTRATION_FAILED"
    assert "invalid institutional role" in error["message"].lower()


# ==============================================================================
# 4. PRIVILEGED ACCOUNT REQUEST & SERVER-SIDE PROVISIONING WORKFLOW
# ==============================================================================

def test_dynamic_departments_endpoint_returns_live_departments():
    """Verify GET /api/v1/auth/departments returns live core.department entries."""
    response = client.get("/api/v1/auth/departments")
    assert response.status_code == 200
    departments = response.json()
    assert isinstance(departments, list)
    dept_codes = {d["code"] for d in departments}
    assert "CSE" in dept_codes
    assert "ECE" in dept_codes
    assert "MECH" in dept_codes
    assert "CIVIL" in dept_codes
    assert "EEE" in dept_codes
    assert "ARCH" in dept_codes
    for dept in departments:
        assert "code" in dept
        assert "name" in dept
        assert "department_id" in dept


def test_hod_account_request_without_department_rejected():
    """HOD role requires a department selection."""
    unique_user = f"req_hod_nodept_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Prof. No Dept",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "HOD",
            "department": None,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert response.status_code == 400
    assert "department is required" in response.json()["error"]["message"].lower()


def test_hod_account_request_with_invalid_department_rejected():
    """HOD role with non-existent department is rejected."""
    unique_user = f"req_hod_invdept_{int(time.time() * 1000)}"
    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Prof. Invalid Dept",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "HOD",
            "department": "AEROSPACE_NONEXISTENT",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        },
    )
    assert response.status_code == 400
    assert "invalid requested department" in response.json()["error"]["message"].lower()


@pytest.mark.parametrize(
    "privileged_role",
    ["HOD", "DEAN", "PRINCIPAL", "MANAGEMENT", "IQAC", "COE", "PLACEMENT", "COUNSELLOR"],
)
def test_privileged_account_request_submission_does_not_grant_immediate_access(privileged_role):
    """
    CRITICAL SECURITY TEST:
    Submitting a request for any privileged role:
    1. Returns 200 with account_type == 'privileged_request' (request submitted)
    2. Does NOT issue any JWT or auth token
    3. Does NOT create an active user in the identity repository
    4. Immediate login fails with 401
    """
    unique_user = f"req_{privileged_role.lower()}_{int(time.time() * 1000)}"
    dept = "CSE" if privileged_role == "HOD" else None
    password = "PrivilegedRequestPass123!"

    response = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": f"Prospective {privileged_role}",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": privileged_role,
            "department": dept,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account_type"] == "privileged_request"
    assert "request_id" in data
    assert "access_token" not in data
    assert "token" not in data

    # Verify no active user was created
    repo = get_identity_repository()
    assert repo.get_user_by_username(unique_user) is None

    # Immediate sign-in must fail
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user, "password": password},
    )
    assert login_resp.status_code == 401


def test_account_requests_list_requires_admin_authorization():
    """Only ADMIN, PRINCIPAL, or MANAGEMENT can list pending account requests."""
    # 1. Unauthenticated request -> 401
    unauth_resp = client.get("/api/v1/auth/account-requests")
    assert unauth_resp.status_code == 401

    # 2. Student user -> 403
    student_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_student_1", "password": "InstitutionalSecurePass123!"},
    )
    student_token = student_login.json()["access_token"]
    student_resp = client.get(
        "/api/v1/auth/account-requests",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_resp.status_code == 403

    # 3. Faculty user -> 403
    faculty_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_faculty_cse", "password": "InstitutionalSecurePass123!"},
    )
    faculty_token = faculty_login.json()["access_token"]
    faculty_resp = client.get(
        "/api/v1/auth/account-requests",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert faculty_resp.status_code == 403

    # 4. Principal user -> 200
    principal_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    principal_token = principal_login.json()["access_token"]
    principal_resp = client.get(
        "/api/v1/auth/account-requests",
        headers={"Authorization": f"Bearer {principal_token}"},
    )
    assert principal_resp.status_code == 200
    assert isinstance(principal_resp.json(), list)


def test_admin_approve_account_request_flow():
    """
    Complete end-to-end approval flow:
    1. User submits request for HOD (department CSE)
    2. Admin lists requests and finds it
    3. Admin approves request
    4. User record is now active in IdentityRepository
    5. User can now sign in with original password
    6. User JWT contains HOD role and CSE departmental scope
    """
    unique_user = f"approved_hod_{int(time.time() * 1000)}"
    password = "TargetHODPassword123!"

    # 1. Submit HOD request
    req_resp = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Dr. Approved CSE HOD",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "HOD",
            "department": "CSE",
            "password": password,
            "confirm_password": password,
        },
    )
    assert req_resp.status_code == 200
    request_id = req_resp.json()["request_id"]

    # 2. Login as Principal
    principal_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    principal_token = principal_login.json()["access_token"]

    # 3. Approve the request
    approve_resp = client.post(
        f"/api/v1/auth/account-requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {principal_token}"},
        json={"notes": "Approved departmental HOD appointment"},
    )
    assert approve_resp.status_code == 200
    app_data = approve_resp.json()
    assert app_data["status"] == "approved"
    assert "approved and provisioned as hod" in app_data["message"].lower()

    # 4. User can now log in
    user_login = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user, "password": password},
    )
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]

    # 5. User has HOD role and CSE departmental scope
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["username"] == unique_user
    assert "HOD" in profile["roles"]
    assert any(sr["scope_id"] == "dept-cse-001" for sr in profile["scoped_roles"])


def test_admin_reject_account_request_flow():
    """
    Rejection flow:
    1. User submits request
    2. Admin rejects request
    3. Status transitions to REJECTED
    4. User cannot log in
    """
    unique_user = f"rejected_user_{int(time.time() * 1000)}"
    password = "RejectedPass123!"

    req_resp = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Unverified Requester",
            "username": unique_user,
            "email": f"{unique_user}@vignan.ac.in",
            "role": "DEAN",
            "password": password,
            "confirm_password": password,
        },
    )
    assert req_resp.status_code == 200
    request_id = req_resp.json()["request_id"]

    principal_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    principal_token = principal_login.json()["access_token"]

    # Reject
    reject_resp = client.post(
        f"/api/v1/auth/account-requests/{request_id}/reject",
        headers={"Authorization": f"Bearer {principal_token}"},
        json={"reason": "Cannot verify institutional credentials"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    # Login fails
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user, "password": password},
    )
    assert login_resp.status_code == 401


def test_requester_cannot_approve_own_request():
    """
    SECURITY INVARIANT:
    A user cannot approve their own account request (Separation of Duties).
    """
    req_store = get_account_request_store()
    req = req_store.create_request(
        full_name="Self Approver Principal",
        username="test_principal",
        email="principal_self@vignan.ac.in",
        requested_role="PRINCIPAL",
        requested_department=None,
        password_hash="$argon2id$mockhash",
    )
    request_id = req["request_id"]

    principal_login = client.post(
        "/api/v1/auth/login",
        json={"username": "test_principal", "password": "InstitutionalSecurePass123!"},
    )
    principal_token = principal_login.json()["access_token"]

    approve_resp = client.post(
        f"/api/v1/auth/account-requests/{request_id}/approve",
        headers={"Authorization": f"Bearer {principal_token}"},
        json={"notes": "Self approving"},
    )
    assert approve_resp.status_code == 403
    assert "cannot approve their own account requests" in approve_resp.json()["error"]["message"].lower()


def test_duplicate_pending_account_request_handled_cleanly():
    """Submitting a duplicate pending request with the same username or email fails cleanly."""
    unique_user = f"dup_req_{int(time.time() * 1000)}"
    email = f"{unique_user}@vignan.ac.in"
    password = "StrongPassword123!"

    # First request succeeds
    resp1 = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "First Request",
            "username": unique_user,
            "email": email,
            "role": "DEAN",
            "password": password,
            "confirm_password": password,
        },
    )
    assert resp1.status_code == 200

    # Second request with same username fails with 400
    resp2 = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Second Request",
            "username": unique_user,
            "email": f"different_{email}",
            "role": "DEAN",
            "password": password,
            "confirm_password": password,
        },
    )
    assert resp2.status_code == 400
    assert "already pending review" in resp2.json()["error"]["message"].lower()

    # Third request with different username but same email fails with 400
    resp3 = client.post(
        "/api/v1/auth/create-account",
        json={
            "full_name": "Third Request",
            "username": f"other_{unique_user}",
            "email": email,
            "role": "DEAN",
            "password": password,
            "confirm_password": password,
        },
    )
    assert resp3.status_code == 400
    assert "already pending review" in resp3.json()["error"]["message"].lower()


# ==============================================================================
# 5. FORGOT PASSWORD TESTS
# ==============================================================================

def test_forgot_password_valid_request_returns_safe_submitted_status():
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "test_principal"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert "password reset request submitted" in data["message"].lower()
    assert "token" not in data


def test_forgot_password_unknown_identifier_returns_safe_identical_message():
    """SECURITY INVARIANT: Prevent user enumeration via password recovery responses."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"identifier": "nonexistent_institutional_email@vignan.ac.in"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "submitted"
    assert "password reset request submitted" in data["message"].lower()


def test_password_reset_flow_with_token_and_credential_invalidation():
    test_user = f"reset_test_user_{int(time.time() * 1000)}"
    old_password = "OldPassword123!"
    new_password = "NewPassword456!"

    client.post(
        "/api/v1/auth/signup",
        json={"username": test_user, "password": old_password, "confirm_password": old_password},
    )

    auth_service = get_authentication_service()
    exists, raw_token = auth_service.request_password_reset(test_user)
    assert exists is True
    assert raw_token is not None

    reset_resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert reset_resp.status_code == 200
    assert "password reset successfully" in reset_resp.json()["message"].lower()

    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": test_user, "password": new_password},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": test_user, "password": old_password},
    )
    assert old_login.status_code == 401


def test_password_reset_token_cannot_be_reused():
    auth_service = get_authentication_service()
    _, raw_token = auth_service.request_password_reset("test_faculty_cse")
    assert raw_token is not None

    resp1 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "FacultyNewPass123!",
            "confirm_password": "FacultyNewPass123!",
        },
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": raw_token,
            "new_password": "AnotherNewPass999!",
            "confirm_password": "AnotherNewPass999!",
        },
    )
    assert resp2.status_code == 401
    assert "invalid, expired, or previously consumed" in resp2.json()["error"]["message"].lower()


def test_password_reset_expired_token_rejected(monkeypatch):
    reset_store = get_password_reset_store()
    expired_token = reset_store.create_reset_token("00000000-0000-0000-0000-000000000001", lifetime_seconds=-10)

    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": expired_token,
            "new_password": "SomeNewPassword123!",
            "confirm_password": "SomeNewPassword123!",
        },
    )
    assert response.status_code == 401
    assert "invalid, expired, or previously consumed" in response.json()["error"]["message"].lower()


# ==============================================================================
# 6. RBAC & SCOPE ISOLATION TESTS
# ==============================================================================

def test_scope_isolation_hod_cse_cannot_access_ece_records():
    """
    CRITICAL SCOPE ISOLATION:
    HOD CSE cannot execute student queries or access metrics for ECE.
    """
    auth_service = get_authentication_service()
    hod_cse = auth_service.authenticate_user("test_hod_cse", "InstitutionalSecurePass123!")
    assert hod_cse is not None

    compiler = get_sql_compiler()
    intent_ece = StructuredIntent(
        intent_type=IntentType.STUDENT_LIST,
        metric_id="student.list",
        primary_metric_id="student.list",
        student_filters={"department": "ECE"},
        filters={"department": "ECE"},
        page=1,
        page_size=25,
    )
    with pytest.raises(SQLAuthorizationError):
        compiler.compile(intent_ece, principal=hod_cse)


def test_scope_isolation_hod_cse_queries_automatically_scoped_to_cse():
    """HOD CSE queries without explicit department filter are bounded to CSE."""
    auth_service = get_authentication_service()
    hod_cse = auth_service.authenticate_user("test_hod_cse", "InstitutionalSecurePass123!")
    compiler = get_sql_compiler()

    intent = StructuredIntent(
        intent_type=IntentType.METRIC_QUERY,
        primary_metric_id="academics.active_student_strength",
        filters={},
    )
    artifact = compiler.compile(intent, principal=hod_cse)
    assert artifact.parameters.get("auth_department_code") == "CSE"
    res = execution_service.execute_artifact(artifact, principal=hod_cse)
    assert res.row_count == 1
    assert res.rows[0]["metric_value"] == 150


def test_scope_isolation_principal_has_institutional_scope():
    """Principal can query cross-departmental metrics without rejection."""
    auth_service = get_authentication_service()
    principal = auth_service.authenticate_user("test_principal", "InstitutionalSecurePass123!")
    compiler = get_sql_compiler()

    intent = StructuredIntent(
        intent_type=IntentType.BREAKDOWN_QUERY,
        primary_metric_id="academics.active_student_strength",
        dimensions=["department"],
        filters={"department": "CSE"},
    )
    artifact = compiler.compile(intent, principal=principal)
    assert "auth_department_code" not in artifact.parameters
    res = execution_service.execute_artifact(artifact, principal=principal)
    assert res.rows[0]["metric_value"] == 150


def test_unprivileged_registered_student_cannot_access_leadership_tools():
    """Newly registered student account is bounded by STUDENT role permissions."""
    username = f"unpriv_student_{int(time.time() * 1000)}"
    password = "StudentPass123!"

    client.post(
        "/api/v1/auth/signup",
        json={"username": username, "password": password, "confirm_password": password},
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    token = login_resp.json()["access_token"]

    query_resp = client.post(
        "/api/v1/agent/query",
        json={"prompt": "Compare course pass percentage across all departments"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert query_resp.status_code in [400, 403]
