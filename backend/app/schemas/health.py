"""
Agent 63 – Health & Readiness Schemas
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseResponse


class HealthResponse(BaseResponse):
    """Basic liveness response schema."""
    status: str = Field("ok", description="Service liveness state")
    service: str = Field("agent63-backend", description="Service identifier")
    version: str = Field(..., description="Application semantic version")


class DependenciesStatus(BaseModel):
    """Health breakdown of internal and external dependencies."""
    schema_registry: str = Field(..., description="Phase 1 schema registry availability status ('ready', 'unavailable')")
    college_database: str = Field(..., description="College PostgreSQL database status ('not_configured', 'configured')")
    schema_registry_objects: Optional[int] = Field(None, description="Number of validated objects in loaded registry")
    database_host: Optional[str] = Field(None, description="Configured database host (host name only, credentials redacted)")
    groq: Optional[str] = Field("not_configured", description="Groq provider configuration status ('configured', 'not_configured'). Indicates credentials/configuration presence only; does NOT perform a live upstream API call to preserve provider quota.")
    gemini: Optional[str] = Field("not_configured", description="Legacy Google Gemini status ('configured', 'not_configured') retained for backward compatibility.")


class ReadinessResponse(BaseResponse):
    """Detailed dependency readiness response schema."""
    status: str = Field(..., description="Overall readiness state ('ready', 'degraded')")
    service: str = Field("agent63-backend", description="Service identifier")
    version: str = Field(..., description="Application semantic version")
    dependencies: DependenciesStatus
