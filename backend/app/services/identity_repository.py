"""
Agent 63 – Identity Repository Abstraction & Non-Production Fixtures
Models database access to identity.app_user, identity.role, identity.permission,
and identity.user_role. Provides an in-memory repository for development and automated testing
without requiring a live PostgreSQL connection.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set
import uuid

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopedRoleAssignment, ScopeType

logger = get_logger("agent63.services.identity_repository")

# Authoritative role-to-permission mapping based on identity.permission and identity.role_permission
ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    "PRINCIPAL": {
        "analytics.read",
        "attendance.read",
        "assessment.read",
        "outcomes.read",
        "placement.read",
        "academics.read",
        "quality.read",
        "export.create",
    },
    "IQAC": {
        "analytics.read",
        "quality.read",
        "outcomes.read",
        "attendance.read",
        "assessment.read",
        "academics.read",
    },
    "DEAN": {
        "analytics.read",
        "attendance.read",
        "assessment.read",
        "outcomes.read",
        "placement.read",
        "academics.read",
    },
    "HOD": {
        "analytics.read",
        "attendance.read",
        "assessment.read",
        "outcomes.read",
        "placement.read",
        "academics.read",
    },
    "COE": {
        "assessment.read",
        "outcomes.read",
    },
    "FACULTY": {
        "attendance.read",
        "assessment.read",
        "outcomes.read",
        "academics.read",
    },
    "MENTOR": {
        "attendance.read",
        "assessment.read",
    },
    "PLACEMENT": {
        "placement.read",
        "academics.read",
    },
    "STUDENT": {
        "attendance.read",
        "assessment.read",
        "outcomes.read",
    },
    "COUNSELLOR": {
        "counselling.read",
        "attendance.read",   # permitted ONLY for assigned mentees (enforced by authorization layer)
        "assessment.read",   # permitted ONLY for assigned mentees (enforced by authorization layer)
    },
    "MANAGEMENT": {
        "analytics.read",
        "academics.read",
        "attendance.read",
        "assessment.read",
        "outcomes.read",
        "placement.read",
        "quality.read",
        "export.create",
    },
    "ADMIN": {
        "system.admin",
        "analytics.read",
    },
}


class IdentityRepository(ABC):
    """Abstract identity persistence contract modeling identity.* schema."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by username."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by user_id."""
        pass

    @abstractmethod
    def get_scoped_roles(self, user_id: str) -> List[ScopedRoleAssignment]:
        """Retrieves scoped role assignments for a user."""
        pass

    @abstractmethod
    def resolve_principal(self, user_id: str) -> Optional[AuthenticatedPrincipal]:
        """Resolves the complete authenticated principal with current trusted roles and permissions."""
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by registered email address."""
        pass

    @abstractmethod
    def get_credential_hash(self, user_id: str) -> Optional[str]:
        """Retrieves stored password hash for internal verification only."""
        pass

    @abstractmethod
    def register_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        scoped_roles: List[ScopedRoleAssignment],
        person_id: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """Registers a new institutional user into identity persistence."""
        pass

    @abstractmethod
    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        """Updates stored credential hash for an institutional user."""
        pass


class InMemoryIdentityRepository(IdentityRepository):
    """
    Non-production in-memory implementation of the identity repository.
    Populated with verified, clearly-demarcated institutional test fixtures.
    """

    def __init__(self):
        # Maps user_id -> user dict
        self._users: Dict[str, Dict[str, Any]] = {}
        # Maps username -> user_id
        self._username_index: Dict[str, str] = {}
        # Maps user_id -> List[ScopedRoleAssignment]
        self._user_roles: Dict[str, List[ScopedRoleAssignment]] = {}
        # Maps user_id -> Argon2id password hash
        self._credentials: Dict[str, str] = {}

    def register_test_user(
        self,
        user_id: str,
        username: str,
        email: str,
        password_hash: str,
        scoped_roles: List[ScopedRoleAssignment],
        person_id: Optional[str] = None,
        is_active: bool = True,
        is_service_account: bool = False,
    ) -> None:
        """Registers a non-production test fixture into the in-memory repository."""
        self._users[user_id] = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "person_id": person_id,
            "is_active": is_active,
            "is_service_account": is_service_account,
        }
        self._username_index[username.lower()] = user_id
        self._user_roles[user_id] = scoped_roles
        self._credentials[user_id] = password_hash

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        uid = self._username_index.get(username.lower())
        if uid:
            return self._users.get(uid)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._users.get(user_id)

    def get_scoped_roles(self, user_id: str) -> List[ScopedRoleAssignment]:
        return self._user_roles.get(user_id, [])

    def get_credential_hash(self, user_id: str) -> Optional[str]:
        """Retrieves stored password hash for internal verification only."""
        return self._credentials.get(user_id)

    def resolve_principal(self, user_id: str) -> Optional[AuthenticatedPrincipal]:
        user = self._users.get(user_id)
        if not user:
            return None

        scoped_roles = self._user_roles.get(user_id, [])
        role_codes = list({sr.role.upper() for sr in scoped_roles})

        # Resolve complete permissions from role permissions map
        permissions: Set[str] = set()
        for role_code in role_codes:
            perms = ROLE_PERMISSIONS_MAP.get(role_code, set())
            permissions.update(perms)

        return AuthenticatedPrincipal(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            person_id=user.get("person_id"),
            is_active=user["is_active"],
            is_service_account=user.get("is_service_account", False),
            roles=role_codes,
            scoped_roles=scoped_roles,
            permissions=permissions,
        )

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        for u in self._users.values():
            if u.get("email", "").lower() == clean_email:
                return u
        return None

    def register_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        scoped_roles: List[ScopedRoleAssignment],
        person_id: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        clean_username = username.strip().lower()
        if clean_username in self._username_index:
            raise ValueError(f"Username '{username}' already exists.")
        user_id = str(uuid.uuid4())
        user_dict = {
            "user_id": user_id,
            "username": username.strip(),
            "email": email.strip().lower(),
            "person_id": person_id,
            "is_active": is_active,
            "is_service_account": False,
        }
        self._users[user_id] = user_dict
        self._username_index[clean_username] = user_id
        self._user_roles[user_id] = scoped_roles
        self._credentials[user_id] = password_hash
        return user_dict

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        if user_id in self._users:
            self._credentials[user_id] = new_password_hash
            return True
        return False


class UnavailableIdentityRepository(IdentityRepository):
    """
    Production fail-closed identity repository stub.
    Used in production or non-test configurations when the real college database
    identity source is unconfigured.
    Guarantees that unconfigured production environments fail closed rather than
    silently falling back to in-memory test fixtures.
    """

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        logger.warning(
            f"Identity lookup for '{username}' failed-closed: real institutional identity "
            "database is not configured or unavailable."
        )
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        logger.warning(
            f"Identity lookup for user_id '{user_id}' failed-closed: real institutional identity "
            "database is not configured or unavailable."
        )
        return None

    def get_scoped_roles(self, user_id: str) -> List[ScopedRoleAssignment]:
        return []

    def resolve_principal(self, user_id: str) -> Optional[AuthenticatedPrincipal]:
        logger.warning(
            f"Principal resolution for user_id '{user_id}' failed-closed: real institutional identity "
            "database is not configured or unavailable."
        )
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return None

    def get_credential_hash(self, user_id: str) -> Optional[str]:
        return None

    def register_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        scoped_roles: List[ScopedRoleAssignment],
        person_id: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        raise RuntimeError("Identity registration unavailable: database not configured.")

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        return False


class DatabaseIdentityRepository(IdentityRepository):
    """
    Production-safe database-backed implementation of IdentityRepository.
    Directly queries identity.app_user, identity.user_role, identity.role,
    and identity.auth_credential using CollegeDatabaseService.
    """

    def __init__(self, db_service: Optional[Any] = None):
        self._db = db_service

    @property
    def db(self) -> Any:
        if self._db is None:
            from backend.app.services.database import college_database_service
            self._db = college_database_service
        return self._db

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT user_id, username, email, person_id, is_active, is_service_account
        FROM identity.app_user
        WHERE lower(username) = lower(:username)
        LIMIT 1;
        """
        try:
            _, rows, _, _ = self.db.execute_query(sql, {"username": username.strip()})
            if not rows:
                return None
            row = rows[0]
            return {
                "user_id": str(row["user_id"]),
                "username": row["username"],
                "email": row["email"],
                "person_id": str(row["person_id"]) if row.get("person_id") else None,
                "is_active": bool(row["is_active"]),
                "is_service_account": bool(row.get("is_service_account", False)),
            }
        except Exception as exc:
            logger.error("Database user lookup failed for username '%s': %s", username, exc)
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT user_id, username, email, person_id, is_active, is_service_account
        FROM identity.app_user
        WHERE user_id = :user_id::uuid
        LIMIT 1;
        """
        try:
            _, rows, _, _ = self.db.execute_query(sql, {"user_id": str(user_id)})
            if not rows:
                return None
            row = rows[0]
            return {
                "user_id": str(row["user_id"]),
                "username": row["username"],
                "email": row["email"],
                "person_id": str(row["person_id"]) if row.get("person_id") else None,
                "is_active": bool(row["is_active"]),
                "is_service_account": bool(row.get("is_service_account", False)),
            }
        except Exception as exc:
            logger.error("Database user lookup failed for user_id '%s': %s", user_id, exc)
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT user_id, username, email, person_id, is_active, is_service_account
        FROM identity.app_user
        WHERE lower(email) = lower(:email)
        LIMIT 1;
        """
        try:
            _, rows, _, _ = self.db.execute_query(sql, {"email": email.strip()})
            if not rows:
                return None
            row = rows[0]
            return {
                "user_id": str(row["user_id"]),
                "username": row["username"],
                "email": row["email"],
                "person_id": str(row["person_id"]) if row.get("person_id") else None,
                "is_active": bool(row["is_active"]),
                "is_service_account": bool(row.get("is_service_account", False)),
            }
        except Exception as exc:
            logger.error("Database user lookup failed for email '%s': %s", email, exc)
            return None

    def get_scoped_roles(self, user_id: str) -> List[ScopedRoleAssignment]:
        sql = """
        SELECT r.code AS role_code, ur.scope_type, ur.scope_id
        FROM identity.user_role ur
        JOIN identity.role r ON ur.role_id = r.role_id
        WHERE ur.user_id = :user_id::uuid
          AND ur.valid_from <= CURRENT_DATE
          AND (ur.valid_to IS NULL OR ur.valid_to >= CURRENT_DATE);
        """
        try:
            _, rows, _, _ = self.db.execute_query(sql, {"user_id": str(user_id)})
            scoped_roles: List[ScopedRoleAssignment] = []
            for r in rows:
                try:
                    scope_type = ScopeType(r["scope_type"])
                except ValueError:
                    logger.warning("Unrecognized scope_type '%s' for user %s", r.get("scope_type"), user_id)
                    continue
                scoped_roles.append(
                    ScopedRoleAssignment(
                        role=r["role_code"],
                        scope_type=scope_type,
                        scope_id=str(r["scope_id"]) if r.get("scope_id") else None,
                    )
                )
            return scoped_roles
        except Exception as exc:
            logger.error("Database scoped role lookup failed for user_id '%s': %s", user_id, exc)
            return []

    def resolve_principal(self, user_id: str) -> Optional[AuthenticatedPrincipal]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        scoped_roles = self.get_scoped_roles(user_id)
        role_codes = list({sr.role.upper() for sr in scoped_roles})

        # Resolve complete permissions from authoritative role permissions map
        permissions: Set[str] = set()
        for role_code in role_codes:
            perms = ROLE_PERMISSIONS_MAP.get(role_code, set())
            permissions.update(perms)

        return AuthenticatedPrincipal(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            person_id=user.get("person_id"),
            is_active=user["is_active"],
            is_service_account=user.get("is_service_account", False),
            roles=role_codes,
            scoped_roles=scoped_roles,
            permissions=permissions,
        )

    def get_credential_hash(self, user_id: str) -> Optional[str]:
        sql = """
        SELECT password_hash
        FROM identity.auth_credential
        WHERE user_id = :user_id::uuid
        LIMIT 1;
        """
        try:
            _, rows, _, _ = self.db.execute_query(sql, {"user_id": str(user_id)})
            if rows and rows[0].get("password_hash"):
                return str(rows[0]["password_hash"])
        except Exception as exc:
            logger.error("Database credential lookup failed for user_id '%s': %s", user_id, exc)
        return None

    def register_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        scoped_roles: List[ScopedRoleAssignment],
        person_id: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "Direct user registration is not supported through read-only CollegeDatabaseService. "
            "Use the dedicated provisioning script."
        )

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        raise NotImplementedError(
            "Direct password update is not supported through read-only CollegeDatabaseService. "
            "Use the dedicated provisioning script."
        )


# Global singleton repository
_identity_repository: Optional[IdentityRepository] = None


def get_identity_repository() -> IdentityRepository:
    """
    Returns the active identity repository based on configuration and security boundaries.

    CRITICAL SECURITY INVARIANTS:
    1. Production runtime must NEVER silently use in-memory test fixtures.
    2. If APP_ENV == 'production' or ALLOW_TEST_FIXTURES is False:
       Returns DatabaseIdentityRepository if college database is configured.
       Returns UnavailableIdentityRepository (fail-closed) if unconfigured or unavailable.
    3. Test suites may explicitly inject an InMemoryIdentityRepository using set_identity_repository().
    4. If APP_ENV != 'production' and ALLOW_TEST_FIXTURES is True:
       Falls back to InMemoryIdentityRepository with verified test fixtures for development and test isolation.
    """
    global _identity_repository
    if _identity_repository is not None:
        return _identity_repository

    from backend.app.services.database import college_database_service

    is_db_configured = settings.is_database_configured and college_database_service.is_configured()

    # In production or whenever test fixtures are disabled:
    if settings.APP_ENV == "production" or not settings.ALLOW_TEST_FIXTURES:
        if is_db_configured:
            logger.info("Initializing production DatabaseIdentityRepository connected to college database.")
            _identity_repository = DatabaseIdentityRepository(college_database_service)
            return _identity_repository
        else:
            logger.warning(
                "Production/fail-closed mode active (ALLOW_TEST_FIXTURES=False or APP_ENV=production) "
                "and college database is NOT configured. Failing closed."
            )
            _identity_repository = UnavailableIdentityRepository()
            return _identity_repository

    # In-memory test fixtures ONLY allowable in explicit testing/development mode with ALLOW_TEST_FIXTURES=True
    logger.info("Initializing TEST-ONLY InMemoryIdentityRepository with non-production test fixtures.")
    repo = InMemoryIdentityRepository()
    _seed_default_test_fixtures(repo)
    _identity_repository = repo
    return _identity_repository


def set_identity_repository(repo: IdentityRepository) -> None:
    """Allows test suites to inject customized repository instances."""
    global _identity_repository
    _identity_repository = repo


def reset_identity_repository() -> None:
    """Resets global singleton repository for isolated test runs."""
    global _identity_repository
    _identity_repository = None



def _seed_default_test_fixtures(repo: InMemoryIdentityRepository) -> None:
    """
    Initializes non-production test fixture users with Argon2id pre-hashed passwords.
    Clearly marked for development and automated testing only.
    Password for all test fixtures: 'InstitutionalSecurePass123!'
    """
    from backend.app.services.password import get_password_manager

    pwd_mgr = get_password_manager()
    default_hash = pwd_mgr.hash_password("InstitutionalSecurePass123!")

    fixtures = [
        # 1. Principal: Institution-wide leadership
        {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "username": "test_principal",
            "email": "principal@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)
            ],
            "is_active": True,
        },
        # 2. IQAC Director: Quality & accreditation analytics
        {
            "user_id": "00000000-0000-0000-0000-000000000002",
            "username": "test_iqac",
            "email": "iqac.director@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="IQAC", scope_type=ScopeType.INSTITUTION)
            ],
            "is_active": True,
        },
        # 3. Dean: Campus / School level scope
        {
            "user_id": "00000000-0000-0000-0000-000000000003",
            "username": "test_dean",
            "email": "dean.engineering@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="DEAN", scope_type=ScopeType.CAMPUS, scope_id="campus-main-001"
                )
            ],
            "is_active": True,
        },
        # 4. HOD Computer Science: Departmental scope (CSE)
        {
            "user_id": "00000000-0000-0000-0000-000000000004",
            "username": "test_hod_cse",
            "email": "hod.cse@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-cse-001"
                )
            ],
            "is_active": True,
        },
        # 5. HOD Electronics: Departmental scope (ECE)
        {
            "user_id": "00000000-0000-0000-0000-000000000005",
            "username": "test_hod_ece",
            "email": "hod.ece@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="HOD", scope_type=ScopeType.DEPARTMENT, scope_id="dept-ece-002"
                )
            ],
            "is_active": True,
        },
        # 6. Faculty (CSE): Offering level scope
        {
            "user_id": "00000000-0000-0000-0000-000000000006",
            "username": "test_faculty_cse",
            "email": "faculty.cse@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="FACULTY",
                    scope_type=ScopeType.COURSE_OFFERING,
                    scope_id="offering-cs101-001",
                )
            ],
            "is_active": True,
        },
        # 7. Multi-Role Faculty + Mentor: Offering + Self (mentees) scope
        {
            "user_id": "00000000-0000-0000-0000-000000000007",
            "username": "test_mentor_faculty",
            "email": "mentor.cse@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="FACULTY",
                    scope_type=ScopeType.COURSE_OFFERING,
                    scope_id="offering-cs101-001",
                ),
                ScopedRoleAssignment(
                    role="MENTOR",
                    scope_type=ScopeType.SELF,
                    scope_id="mentor-faculty-uuid-007",
                ),
            ],
            "is_active": True,
        },
        # 8. Placement Officer: Placement domain institution-wide
        {
            "user_id": "00000000-0000-0000-0000-000000000008",
            "username": "test_placement",
            "email": "placement.officer@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="PLACEMENT", scope_type=ScopeType.INSTITUTION)
            ],
            "is_active": True,
        },
        # 9. Controller of Examinations (COE)
        {
            "user_id": "00000000-0000-0000-0000-000000000009",
            "username": "test_coe",
            "email": "coe@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="COE", scope_type=ScopeType.INSTITUTION)
            ],
            "is_active": True,
        },
        # 10. Student: Strictly self scope (linked to seeded student 1: Deepak Kumar, 22CSEA001)
        {
            "user_id": "00000000-0000-0000-0000-000000000010",
            "username": "test_student_1",
            "email": "221fa04001@vignan.ac.in",
            "person_id": "a6300000-0020-4000-8000-000000000001",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="STUDENT",
                    scope_type=ScopeType.SELF,
                    scope_id="student-uuid-s101",
                )
            ],
            "is_active": True,
        },
        # 11. Student 2: Different student self scope (linked to seeded student 2: Manish Gupta, 22CSEB001)
        {
            "user_id": "00000000-0000-0000-0000-000000000011",
            "username": "test_student_2",
            "email": "221fa04002@vignan.ac.in",
            "person_id": "a6300000-0020-4000-8000-000000000002",
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="STUDENT",
                    scope_type=ScopeType.SELF,
                    scope_id="student-uuid-s102",
                )
            ],
            "is_active": True,
        },
        # 12. Counsellor: Mentee-scoped counselling support (attendance/assessment for assigned mentees only)
        # person_id links to the faculty record used as mentor_faculty_id in studentlife.mentorship
        {
            "user_id": "00000000-0000-0000-0000-000000000012",
            "username": "test_counsellor",
            "email": "counsellor@vignan.ac.in",
            "person_id": "a6300000-0011-4000-8000-000000000001",  # Dr. Ramesh Kumar, faculty-001
            "scoped_roles": [
                ScopedRoleAssignment(
                    role="COUNSELLOR",
                    scope_type=ScopeType.SELF,
                    scope_id="a6300000-0011-4000-8000-000000000001",
                )
            ],
            "is_active": True,
        },
        # 13. Inactive User: Account disabled
        {
            "user_id": "00000000-0000-0000-0000-000000000013",
            "username": "test_inactive_user",
            "email": "inactive@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="STUDENT", scope_type=ScopeType.SELF)
            ],
            "is_active": False,
        },
        # 14. Management: Executive institutional leadership (DEVELOPMENT/TEST ONLY)
        {
            "user_id": "00000000-0000-0000-0000-000000000014",
            "username": "test_management",
            "email": "management@vignan.ac.in",
            "scoped_roles": [
                ScopedRoleAssignment(role="MANAGEMENT", scope_type=ScopeType.INSTITUTION)
            ],
            "is_active": True,
        },
    ]

    for f in fixtures:
        repo.register_test_user(
            user_id=f["user_id"],
            username=f["username"],
            email=f["email"],
            password_hash=default_hash,
            scoped_roles=f["scoped_roles"],
            person_id=f.get("person_id"),
            is_active=f["is_active"],
        )
