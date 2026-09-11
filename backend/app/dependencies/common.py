"""
Agent 63 – Common Dependencies
Dependency injection providers for FastAPI route handlers.
"""

from backend.app.services.database import CollegeDatabaseService, college_database_service
from backend.app.services.schema_registry import SchemaRegistryService, schema_registry_service


def get_schema_registry() -> SchemaRegistryService:
    """Provides singleton SchemaRegistryService instance."""
    return schema_registry_service


def get_database_service() -> CollegeDatabaseService:
    """Provides singleton CollegeDatabaseService instance."""
    return college_database_service
