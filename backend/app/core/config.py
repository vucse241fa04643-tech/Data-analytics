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

    # Groq Natural Language Intent Configuration (Phase 6 Provider Migration)
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key. Stored exclusively on backend; never exposed to frontend or Git."
    )
    GROQ_MODEL: str = Field(
        default="openai/gpt-oss-20b",
        description="Configured Groq model identifier for structured intent generation."
    )
    GROQ_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout duration in seconds for Groq API invocations."
    )

    # Google Gemini Natural Language Intent Configuration (Phase 6 - Legacy / Alternative)
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key. Stored exclusively on backend; never exposed to frontend or Git."
    )
    GEMINI_MODEL: str = Field(
        default="gemini-3.6-flash",
        description="Configured Google Gemini model identifier for structured intent generation."
    )
    GEMINI_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout duration in seconds for Google Gemini API invocations."
    )

    # SQL Generation & Safety Bounds (Phase 7)
    DEFAULT_QUERY_LIMIT: int = Field(
        default=100,
        description="Default maximum row limit for generated institutional analytical queries."
    )
    MAX_QUERY_LIMIT: int = Field(
        default=1000,
        description="Ceiling limit for any generated analytical query to prevent unbounded resource consumption."
    )

    # Safe SQL Execution & Result Validation (Phase 8)
    COLLEGE_DB_MIN_POOL_SIZE: int = Field(
        default=1,
        description="Minimum connections maintained in the read-only database pool."
    )
    COLLEGE_DB_MAX_POOL_SIZE: int = Field(
        default=10,
        description="Maximum concurrent connections in the read-only database pool."
    )
    MAX_RESULT_ROWS: int = Field(
        default=1000,
        description="Strict upper bound on row count returned from database execution."
    )
    MAX_RESULT_BYTES: int = Field(
        default=1048576,
        description="Maximum allowed byte size (1MB) for serialized query results."
    )

    # Conversation Context & Follow-Up Analytics (Phase 10)
    CONVERSATION_CONTEXT_TTL_SECONDS: int = Field(
        default=1800,
        description="Time-to-live in seconds for active conversation context (default 30 minutes)."
    )
    CONVERSATION_MAX_TURNS: int = Field(
        default=10,
        description="Maximum number of turns allowed in a single conversation thread."
    )
    CONVERSATION_MAX_ENTRIES: int = Field(
        default=1000,
        description="Maximum concurrent active conversation contexts in memory (LRU eviction)."
    )
    CONVERSATION_MAX_SIZE_BYTES: int = Field(
        default=32768,
        description="Maximum serialized byte ceiling (32KB) for a single conversation context."
    )

    # Deterministic Anomaly Detection (Phase 11)
    ANOMALY_DETECTION_ENABLED: bool = Field(
        default=True,
        description="Enable deterministic anomaly detection on validated QueryResults."
    )
    ANOMALY_ATTENDANCE_THRESHOLD: float = Field(
        default=75.0,
        description="Configured analytical benchmark for attendance percentage (below which results are flagged as anomalous)."
    )
    ANOMALY_PASS_RATE_THRESHOLD: float = Field(
        default=60.0,
        description="Configured analytical benchmark for pass percentage (below which results are flagged as anomalous)."
    )
    ANOMALY_ATTAINMENT_THRESHOLD: float = Field(
        default=2.0,
        description="Configured analytical benchmark for outcome attainment level on 3-point scale."
    )
    ANOMALY_HISTORICAL_MIN_OBSERVATIONS: int = Field(
        default=3,
        description="Minimum observations required to calculate historical statistical anomaly."
    )
    ANOMALY_Z_SCORE_THRESHOLD: float = Field(
        default=2.0,
        description="Standard deviation multiple (z-score) required to flag a statistical anomaly."
    )

    # Role-Based Institutional Dashboards & Scheduled Refresh (Phase 12)
    DASHBOARD_CACHE_ENABLED: bool = Field(
        default=True,
        description="Whether in-memory dashboard result caching is enabled."
    )
    DASHBOARD_CACHE_TTL_SECONDS: int = Field(
        default=300,
        description="TTL in seconds for cached dashboard results (default 5 minutes)."
    )
    DASHBOARD_MAX_WIDGETS_PER_DASHBOARD: int = Field(
        default=8,
        description="Maximum widgets allowed per dashboard to bound execution load."
    )
    DASHBOARD_MAX_CONCURRENT_WIDGET_EXECUTIONS: int = Field(
        default=3,
        description="Maximum concurrent widget executions per dashboard request."
    )
    DASHBOARD_SCHEDULER_ENABLED: bool = Field(
        default=False,
        description=(
            "Whether the in-process dashboard refresh scheduler is enabled. "
            "Defaults to False to prevent background threads during testing and local development. "
            "Set DASHBOARD_SCHEDULER_ENABLED=true in production .env to enable scheduled refresh. "
            "The scheduler can always be triggered manually via POST /{dashboard_id}/refresh."
        ),
    )
    DASHBOARD_SCHEDULE_MIN_INTERVAL_MINUTES: int = Field(
        default=60,
        description="Minimum allowed refresh interval in minutes (default 60 minutes, prevents polling abuse)."
    )
    DASHBOARD_MAX_SCHEDULES_PER_USER: int = Field(
        default=5,
        description="Maximum active refresh schedules allowed per user."
    )
    DASHBOARD_MAX_TOTAL_SCHEDULES: int = Field(
        default=50,
        description="Maximum active refresh schedules system-wide."
    )

    # Analytical Query Logging & Popular-Question Aggregation (Phase 13)
    QUERY_LOG_ENABLED: bool = Field(
        default=True,
        description=(
            "Whether application-level analytical query logging is enabled. "
            "Logging is in-memory only and does NOT write to the college PostgreSQL database. "
            "Set to False to disable all query event collection."
        ),
    )
    QUERY_LOG_MAX_ENTRIES: int = Field(
        default=10000,
        description=(
            "Maximum number of query log events retained in memory. "
            "Oldest events are evicted (LRU) when the limit is reached. "
            "Bounds memory consumption of the query logging subsystem."
        ),
    )
    QUERY_LOG_AGGREGATION_WINDOW_HOURS: int = Field(
        default=168,
        description=(
            "Time window (in hours) for popular-question aggregation (default: 168 = 7 days). "
            "Events older than this window are excluded from popularity calculations. "
            "Does not represent an institutional data retention policy — "
            "this is application-level usage analytics only."
        ),
    )
    QUERY_LOG_MAX_POPULAR_RESULTS: int = Field(
        default=10,
        description=(
            "Maximum number of popular analytical patterns returned by the popular-questions API. "
            "Bounded to prevent overly long response payloads."
        ),
    )
    QUERY_LOG_SAFE_QUERY_LABEL_MAX_LEN: int = Field(
        default=0,
        description=(
            "Maximum character length of the optional safe_query_label field stored per event. "
            "Defaults to 0 (disabled) — raw natural language query text is NOT stored. "
            "Popular questions are derived from metric_id and dimensions, not raw query text. "
            "Set to a positive value (e.g. 200) to store a bounded, sanitized label for debugging. "
            "Never stores SQL, credentials, or confidential content regardless of this setting."
        ),
    )

    # Analytical Result Export & Official Report Verification (Phase 14)
    EXPORT_ENABLED: bool = Field(
        default=True,
        description="Whether analytical query result export (CSV, JSON) is enabled."
    )
    EXPORT_MAX_ROWS: int = Field(
        default=1000,
        description="Strict maximum row ceiling for exported results (matches Phase 8 MAX_RESULT_ROWS)."
    )
    EXPORT_MAX_BYTES: int = Field(
        default=2097152,
        description="Maximum allowed byte size (2MB) for serialized export payloads."
    )
    EXPORT_ARTIFACT_TTL_SECONDS: int = Field(
        default=900,
        description="Time-to-live in seconds for server-side cached analytical export artifacts (default 15 minutes)."
    )
    EXPORT_ARTIFACT_MAX_ENTRIES: int = Field(
        default=1000,
        description="Maximum number of active export artifacts retained in memory (LRU eviction)."
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

    @property
    def is_groq_configured(self) -> bool:
        """Evaluates whether Groq API key is configured."""
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY.strip())

    @property
    def is_gemini_configured(self) -> bool:
        """Evaluates whether Google Gemini API key is configured."""
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())



# Global cached settings instance
settings = Settings()

