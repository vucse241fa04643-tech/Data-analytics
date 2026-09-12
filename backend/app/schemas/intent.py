"""
Agent 63 – Structured Intent Schemas
Defines strict Pydantic schemas for natural language understanding output,
semantic metric references, dimensional groupings, filters, and validation statuses.
Zero SQL or database execution expressions permitted.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class IntentType(str, Enum):
    """Controlled vocabulary of supported analytical intent categories."""
    METRIC_QUERY = "METRIC_QUERY"
    COMPARISON_QUERY = "COMPARISON_QUERY"
    TREND_QUERY = "TREND_QUERY"
    RANKING_QUERY = "RANKING_QUERY"
    BREAKDOWN_QUERY = "BREAKDOWN_QUERY"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSUPPORTED = "UNSUPPORTED"


class IntentValidationStatus(str, Enum):
    """Validation lifecycle status for parsed structured intents."""
    VALID = "VALID"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    REJECTED = "REJECTED"


class TimeContext(BaseModel):
    """Structured temporal scope derived from natural language expressions."""
    academic_year: Optional[str] = Field(
        default=None,
        description="Academic year cycle identifier, e.g. '2024-25'",
    )
    term: Optional[str] = Field(
        default=None,
        description="Instructional period identifier, e.g. 'SEM_1', 'ODD'",
    )
    date_range: Optional[Dict[str, Optional[str]]] = Field(
        default=None,
        description="Explicit calendar date bounds if specified",
    )


class StructuredIntent(BaseModel):
    """
    Normalized, machine-readable analytical intent specification.
    Strictly free from raw SQL, ASTs, or execution mechanics.
    """
    intent_type: IntentType = Field(
        ...,
        description="Categorized intent type corresponding to supported query archetypes",
    )
    metric_id: Optional[str] = Field(
        default=None,
        description="Canonical metric identifier from Phase 4 Semantic Layer (e.g. 'attendance.percentage')",
    )
    primary_metric_id: Optional[str] = Field(
        default=None,
        description="Primary metric identifier (synonymous with metric_id)",
    )
    secondary_metric_ids: List[str] = Field(
        default_factory=list,
        description="Secondary metric identifiers for comparisons or multi-metric queries",
    )
    dimensions: List[str] = Field(
        default_factory=list,
        description="List of verified dimensional group-by attributes (e.g. ['department', 'academic_year'])",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value filtering constraints (e.g. {'department': 'CSE'})",
    )
    time_context: TimeContext = Field(
        default_factory=TimeContext,
        description="Extracted academic temporal parameters",
    )
    reasoning_summary: Optional[str] = Field(
        default=None,
        description="Non-sensitive brief interpretation explanation for transparency",
    )
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Suggested clarification prompts if query is ambiguous",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_metric_ids(cls, values: Any) -> Any:
        if isinstance(values, dict):
            p_id = values.get("primary_metric_id")
            m_id = values.get("metric_id")
            if p_id and not m_id:
                values["metric_id"] = p_id
            elif m_id and not p_id:
                values["primary_metric_id"] = m_id
        return values


    @field_validator("filters")
    @classmethod
    def validate_filters_not_raw_sql(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Defensive barrier against SQL injection or raw clauses in filters."""
        sql_keywords = ["select", "where", "insert", "update", "delete", "drop", "--", ";", "union", "exec"]
        for key, val in v.items():
            str_key = str(key).lower()
            str_val = str(val).lower()
            for kw in sql_keywords:
                if kw in str_key.split() or kw in str_val.split():
                    raise ValueError(f"Raw SQL clause or keyword '{kw}' detected in filter: {key}={val}")
        return v


class IntentRequest(BaseModel):
    """Client request payload containing natural language message."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Institutional analytical question or command in natural language",
        examples=["What is the average attendance of CSE students?"],
    )


class IntentResponse(BaseModel):
    """Complete backend API response envelope for structured intent extraction."""
    status: IntentValidationStatus = Field(
        ...,
        description="Overall validation outcome for the submitted query",
    )
    intent: Optional[StructuredIntent] = Field(
        default=None,
        description="Validated structured intent payload if status is VALID",
    )
    clarification_questions: List[str] = Field(
        default_factory=list,
        description="Clarification prompts if status is CLARIFICATION_REQUIRED",
    )
    message: str = Field(
        default="",
        description="User-facing explanation or guidance note",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Validated request correlation identifier for audit tracing",
    )
