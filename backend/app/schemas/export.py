"""Agent 63 - Phase 14: Export & Verification Schemas
Defines structured request/response models for:
1. Analytical result export (CSV, JSON)
2. Official report verification (MATCH, MISMATCH, NOT_COMPARABLE, NOT_VERIFIED)

SECURITY INVARIANTS:
- No raw SQL statements
- No database credentials or connection details
- No client-supplied result rows (must reference server-side request_id)
- Zero LLM dependencies in schemas
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.schemas.query_result import QueryResult


class ExportArtifact(BaseModel):
    """Server-side cached analytical execution artifact available for export and verification."""
    request_id: str = Field(..., description="Unique request trace ID.")
    user_id: str = Field(..., description="Internal user UUID who executed the query.")
    role: str = Field(..., description="Primary role of the executing user.")
    metric_id: str = Field(..., description="Semantic metric ID.")
    metric_display_name: str = Field(..., description="Human display name from semantic registry.")
    query_type: Optional[str] = Field(default=None)
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    scope_type: Optional[str] = Field(default=None)
    scope_id: Optional[str] = Field(default=None)
    query_result: QueryResult = Field(..., description="Validated execution QueryResult.")
    visualization_type: Optional[str] = Field(default=None)
    anomaly_status: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        + timedelta(seconds=settings.EXPORT_ARTIFACT_TTL_SECONDS)
    )



class ExportFormat(str, Enum):
    """Supported analytical export serialization formats."""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


class ExportRequest(BaseModel):
    """
    Request model for exporting an analytical query result.
    Client supplies ONLY the trusted request_id reference and desired format.
    Does NOT accept arbitrary SQL, table names, or client-provided rows.
    """
    request_id: str = Field(
        ...,
        description="Unique request correlation ID of the already-executed, validated query.",
    )
    format: ExportFormat = Field(
        default=ExportFormat.CSV,
        description="Desired export file format (csv, json, or pdf).",
    )


class ExportMetadata(BaseModel):
    """Safe, privacy-preserving metadata header included with exported artifacts."""
    system: str = Field(
        default="Agent 63 Institutional Analytics",
        description="Generating institutional agent identity.",
    )
    metric_id: str = Field(
        ...,
        description="Authoritative semantic metric ID.",
    )
    metric_display_name: str = Field(
        ...,
        description="Human-readable institutional metric name from semantic registry.",
    )
    query_type: Optional[str] = Field(
        default=None,
        description="Intent type (METRIC_QUERY, COMPARISON, TREND, etc.).",
    )
    dimensions: List[str] = Field(
        default_factory=list,
        description="Dimensions queried in the analytical execution.",
    )
    scope_type: Optional[str] = Field(
        default=None,
        description="Organizational scope type of the query (INSTITUTION, DEPARTMENT, SELF).",
    )
    row_count: int = Field(
        ...,
        ge=0,
        description="Number of exported result rows.",
    )
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of export generation in UTC.",
    )
    verification_status: str = Field(
        default="NOT_VERIFIED",
        description="Official report verification status at time of export.",
    )
    disclaimer: str = Field(
        default=(
            "Exported analytical result from read-only institutional data. "
            "Does not constitute statutory certification or official institutional approval."
        ),
        description="Mandatory institutional disclaimer.",
    )


class ExportResponseJSON(BaseModel):
    """Structured JSON envelope for analytical result exports."""
    export_metadata: ExportMetadata = Field(..., description="Export provenance and metadata.")
    columns: List[str] = Field(..., description="Ordered column names from query result.")
    data: List[Dict[str, Any]] = Field(..., description="Array of validated data records.")


class VerificationStatus(str, Enum):
    """Deterministic comparison outcome between analytical result and official document."""
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    NOT_VERIFIED = "NOT_VERIFIED"


class VerificationRequest(BaseModel):
    """
    Request model for verifying an analytical query result against an official document.
    References an existing authorized request_id.
    """
    request_id: str = Field(
        ...,
        description="Unique request correlation ID of the analytical query to verify.",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional registered document ID from knowledge.document or quality.evidence_item.",
    )


class VerificationResult(BaseModel):
    """
    Structured outcome of deterministic official report verification.
    NEVER declares 'certified' merely because numbers match.
    """
    status: VerificationStatus = Field(
        ...,
        description="Outcome: MATCH, MISMATCH, NOT_COMPARABLE, or NOT_VERIFIED.",
    )
    metric_id: str = Field(
        ...,
        description="Metric ID compared.",
    )
    metric_display_name: str = Field(
        ...,
        description="Human-readable metric name.",
    )
    analytical_value: Optional[Any] = Field(
        default=None,
        description="Value computed by Agent 63 from live database tables.",
    )
    official_value: Optional[Any] = Field(
        default=None,
        description="Value recorded in the registered authoritative institutional document/KPI.",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (e.g. '%', 'count', 'LPA').",
    )
    reporting_period: Optional[str] = Field(
        default=None,
        description="Academic period or year (e.g. '2024-2025', 'SEM-1').",
    )
    scope: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Organizational scope evaluated for comparison.",
    )
    document_reference: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Authoritative document details (title, version, document_class) if found.",
    )
    reason: str = Field(
        ...,
        description="Factual explanation of the comparison result.",
    )
    disclaimer: str = Field(
        default=(
            "Comparison against registered institutional report. "
            "Verification indicates mathematical concordance and does not constitute statutory "
            "certification unless approved by institutional authority."
        ),
        description="Institutional governance statement.",
    )
    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Verification execution timestamp.",
    )
