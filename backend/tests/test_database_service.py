"""
Agent 63 – Test Safe Database Service Abstraction
Validates that the database layer operates safely without requiring PostgreSQL.
"""

import pytest
from backend.app.services.database import CollegeDatabaseService, DatabaseStatus


def test_database_service_unconfigured_by_default():
    """Verify default database status is not_configured."""
    service = CollegeDatabaseService()
    assert service.get_status() == DatabaseStatus.NOT_CONFIGURED
    assert "not configured" in service.get_status_message().lower()


def test_database_service_metadata_is_safe():
    """Verify get_safe_metadata does not contain passwords or raw connection secrets."""
    service = CollegeDatabaseService()
    meta = service.get_safe_metadata()
    assert meta["configured"] is False
    assert "password" not in meta
    assert "user" not in meta
    assert meta["driver"] == "postgresql"


def test_database_service_check_connection_without_postgres():
    """Verify check_connection returns not_configured without attempting socket connections."""
    import asyncio
    service = CollegeDatabaseService()
    result = asyncio.run(service.check_connection())
    assert result["status"] == DatabaseStatus.NOT_CONFIGURED
    assert result["connected"] is False
    assert "not configured" in result["detail"].lower()
