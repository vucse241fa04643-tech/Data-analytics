"""
Agent 63 – Application Configuration
Centralized configuration management via Pydantic Settings.
Safe defaults allow local execution without requiring database credentials.
"""

from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Metadata
    APP_NAME: str = "Agent 63 Institutional Analytics Backend"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api/v1"

    # Server Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Configuration (Restricted by default, accepts comma-separated list or JSON array)
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed origins for Cross-Origin Resource Sharing"
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    # College-Provided PostgreSQL Database (Configured in Phase 1/2)
    # Strictly optional at runtime; missing DB config does NOT prevent startup
    COLLEGE_DB_DRIVER: str = "postgresql"
    COLLEGE_DB_HOST: Optional[str] = None
    COLLEGE_DB_PORT: int = 5432
    COLLEGE_DB_NAME: Optional[str] = "academic_agent_platform"
    COLLEGE_DB_USER: Optional[str] = None
    COLLEGE_DB_PASSWORD: Optional[str] = None
    COLLEGE_DB_SSL_MODE: str = "prefer"
    COLLEGE_DB_CONNECT_TIMEOUT: int = 5
    COLLEGE_DB_STATEMENT_TIMEOUT: int = 5000  # milliseconds (5s max)

    # Schema Registry Path
    SCHEMA_REGISTRY_PATH: Optional[str] = None

    # Semantic Registry Path
    SEMANTIC_REGISTRY_PATH: Optional[str] = None

    # Authentication & JWT Configuration (Phase 5)
    AUTH_ENABLED: bool = True
    JWT_SECRET: Optional[str] = Field(
        default=None,
        description="Cryptographic secret key for JWT signing. Must be at least 32 characters."
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ISSUER: str = "agent63-auth"
    JWT_AUDIENCE: str = "agent63-api"

    # Test Fixture Isolation (Phase 5 Security)
    # Strictly prohibited in production. Only allowable when explicitly enabled in testing/dev.
    ALLOW_TEST_FIXTURES: bool = Field(
        default=False,
        description="Allow in-memory test fixtures only during automated testing or explicit dev mode"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """
        Enforces Phase 5 security constraints:
        1. Test fixtures are strictly prohibited in production.
        2. When AUTH_ENABLED is True, JWT_SECRET must not be empty and must have at least 32 characters.
        3. In production, placeholder, default, or example secrets are strictly rejected.
        """
        if self.APP_ENV == "production" and self.ALLOW_TEST_FIXTURES:
            raise ValueError("ALLOW_TEST_FIXTURES cannot be True in production environment.")

        if self.AUTH_ENABLED:
            if not self.JWT_SECRET or not self.JWT_SECRET.strip():
                raise ValueError(
                    "JWT_SECRET is required and cannot be empty when AUTH_ENABLED is True."
                )
            clean_secret = self.JWT_SECRET.strip()
            if len(clean_secret) < 32:
                raise ValueError(
                    f"JWT_SECRET must be at least 32 characters long for security (got {len(clean_secret)})."
                )

            # Insecure / placeholder checks for production
            if self.APP_ENV == "production":
                normalized = clean_secret.lower()
                exact_insecure = {
                    "secret",
                    "jwt-secret",
                    "default-secret",
                    "dev-secret",
                    "changeme",
                    "change-me",
                    "default",
                    "agent63-dev-secret-change-in-production-min32bytes",
                }
                substring_insecure = [
                    "replace-with",
                    "change-in-production",
                    "placeholder",
                    "example",
                    "agent63-dev",
                ]
                if normalized in exact_insecure or any(s in normalized for s in substring_insecure):
                    raise ValueError(
                        "Insecure default, placeholder, or development JWT_SECRET is not permitted in production."
                    )
        return self

    @property
    def is_database_configured(self) -> bool:
        """Evaluates whether minimum college database connectivity parameters are provided."""
        return bool(
            self.COLLEGE_DB_HOST and
            self.COLLEGE_DB_NAME and
            self.COLLEGE_DB_USER and
            self.COLLEGE_DB_PASSWORD
        )


# Global cached settings instance
settings = Settings()

