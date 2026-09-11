"""
Agent 63 – Common Schemas
Provides reusable Pydantic models for API responses and error envelopes.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseResponse(BaseModel):
    """Base schema for standard API responses."""
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(BaseModel):
    """Structured error payload without sensitive data leaks."""
    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable explanation of error")
    request_id: Optional[str] = Field(None, description="Correlation identifier for request tracing")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context or validation details")


class ErrorResponse(BaseResponse):
    """Enveloped error response model."""
    error: ErrorDetail
