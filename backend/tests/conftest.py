"""
Pytest configuration and shared fixtures for Agent 63 backend tests.
Runs in-memory without requiring PostgreSQL or external services.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import Settings, settings
from backend.app.services.schema_registry import SchemaRegistryService


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def custom_settings():
    """Returns a fresh Settings instance for isolated config tests."""
    return Settings()
