"""Agent 63 - Phase 8: Query Result Schema
Pydantic schemas for database query execution results, metadata, and status.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryResultStatus(str, Enum):
    """Execution status lifecycle states."""
    SUCCESS = "SUCCESS"
    EMPTY = "EMPTY"
    ERROR = "ERROR"
    DATABASE_NOT_CONFIGURED = "DATABASE_NOT_CONFIGURED"


class ExecutionMetadata(BaseModel):
    """Metadata recorded for query execution and result validation."""
    execution_time_ms: float = Field(..., description="Query execution elapsed time in milliseconds")
    row_count: int = Field(..., ge=0, description="Total number of returned rows")
    columns: List[str] = Field(..., description="Ordered list of column names")
    data_types: Dict[str, str] = Field(default_factory=dict, description="Inferred or mapped column data types")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of execution")
    metric_id: Optional[str] = Field(default=None, description="Semantic metric ID associated with execution")
    statement_timeout_ms: Optional[int] = Field(default=None, description="Applied PostgreSQL statement timeout")


class QueryResult(BaseModel):
    """Safe, validated, and normalized result set from read-only execution."""
    status: QueryResultStatus = Field(..., description="Result status (SUCCESS, EMPTY, ERROR, DATABASE_NOT_CONFIGURED)")
    columns: List[str] = Field(default_factory=list, description="Ordered column names")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Validated row dictionaries with column keys")
    row_count: int = Field(default=0, ge=0, description="Total count of validated rows")
    metadata: ExecutionMetadata = Field(..., description="Execution performance and auditing metadata")
    error: Optional[str] = Field(default=None, description="User-safe error description if execution failed")


class AgentQueryRequest(BaseModel):
    """Request payload for the end-to-end agent analytical query endpoint."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language institutional query",
        examples=["What is the average attendance of CSE students?"],
    )
    dry_run: bool = Field(
        default=False,
        description="If true, compiles and validates SQL without executing against PostgreSQL",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Opaque conversation session identifier for multi-turn follow-up queries",
    )


from backend.app.schemas.visualization import VisualizationDescriptor
from backend.app.schemas.anomaly import AnomalyAssessment


class AgentQueryResponse(BaseModel):
    """Response payload containing intent, compiled SQL artifact, and execution results."""
    intent: Optional[Dict[str, Any]] = Field(default=None, description="Extracted and authorized StructuredIntent")
    sql_artifact: Optional[Dict[str, Any]] = Field(default=None, description="Compiled and AST-validated SQL artifact")
    result: Optional[QueryResult] = Field(default=None, description="Validated execution results (null if dry_run or error)")
    execution_metadata: Optional[ExecutionMetadata] = Field(default=None, description="Execution timing and metadata")
    dry_run: bool = Field(default=False, description="Whether execution was skipped due to dry_run mode")
    message: Optional[str] = Field(default=None, description="Informational or guidance message")
    request_id: Optional[str] = Field(default=None, description="Trace request identifier")
    visualization: Optional[VisualizationDescriptor] = Field(default=None, description="Deterministic visualization recommendation")
    explanation: Optional[str] = Field(default=None, description="Deterministic analytical explanation derived from validated data")
    metric_display_name: Optional[str] = Field(default=None, description="Human-readable display name from semantic registry")
    conversation_id: Optional[str] = Field(default=None, description="Opaque identifier for the active conversation")
    is_follow_up: bool = Field(default=False, description="Whether this query inherited context from a prior turn")
    clarification_questions: List[str] = Field(default_factory=list, description="Clarification options if follow-up is ambiguous")
    anomaly: Optional[AnomalyAssessment] = Field(default=None, description="Deterministic anomaly detection assessment")

