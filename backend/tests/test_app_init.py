"""
Agent 63 – Test Application Initialization & Configuration
Validates that the FastAPI application initializes without requiring PostgreSQL or secrets.
"""

from backend.app.core.config import Settings
from backend.app.main import app, create_application


def test_app_initializes_successfully():
    """Verify application factory creates valid FastAPI instance."""
    instance = create_application()
    assert instance.title == "Agent 63 Institutional Analytics Backend"
    assert instance.version == "0.1.0"


def test_settings_safe_defaults(monkeypatch):
    """Verify settings provide safe defaults without needing a live database or credentials."""
    for var in ["COLLEGE_DB_HOST", "COLLEGE_DB_PASSWORD", "COLLEGE_DB_USER", "COLLEGE_DB_NAME"]:
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.APP_ENV == "development"
    assert s.is_database_configured is False
    assert s.COLLEGE_DB_HOST is None
    assert s.COLLEGE_DB_PASSWORD is None
    assert "http://localhost:5173" in s.CORS_ORIGINS


def test_settings_cors_configuration(monkeypatch):
    """Verify CORS origins can be overridden safely via environment variable."""
    monkeypatch.setenv("CORS_ORIGINS", '["https://institution.edu"]')
    s = Settings()
    assert "https://institution.edu" in s.CORS_ORIGINS
    assert len(s.CORS_ORIGINS) == 1
