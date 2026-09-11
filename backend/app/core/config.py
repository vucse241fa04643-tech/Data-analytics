"""
Agent 63 – Application Configuration
Centralized configuration management via Pydantic Settings.
Safe defaults allow local execution without requiring database credentials.
"""

from typing import List, Optional
from pydantic import Field
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

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
