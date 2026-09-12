"""
Agent 63 – SQL Artifact Schemas (Phase 7)
Defines strict Pydantic schemas for compiled, parameterized SQL artifacts.
All artifacts are read-only SELECT queries with separated parameters,
explicitly verified against the Schema Registry and Semantic Layer.
No execution mechanics or database connections in Phase 7.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SQLCompilationStatus(str, Enum):
    """Lifecycle status for SQL compilation pipeline."""
    SQL_COMPILED = "SQL_COMPILED"
    SQL_REJECTED = "SQL_REJECTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSUPPORTED = "UNSUPPORTED"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"


class SQLArtifact(BaseModel):
    """
    Normalized, parameterized SQL artifact compiled from validated StructuredIntent.
    Strictly read-only, fully parameterized, and AST-validated before storage.
    """
    sql: str = Field(
        ...,
        description="Deterministic parameterized PostgreSQL SELECT statement",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Named parameters bound to the SQL statement; user input is never interpolated",
    )
    metric_id: str = Field(
        ...,
        description="Authoritative metric identifier from Phase 4 Semantic Layer",
    )
    tables: List[str] = Field(
        default_factory=list,
        description="List of verified schema-qualified database objects referenced in query",
    )
    columns: List[str] = Field(
        default_factory=list,
        description="List of verified column identifiers referenced in query",
    )
    joins: List[str] = Field(
        default_factory=list,
        description="Verified join path identifiers connecting source objects",
    )
    filters: List[str] = Field(
        default_factory=list,
        description="Semantic filter keys applied in where clause",
    )
    authorization_predicates: List[str] = Field(
        default_factory=list,
        description="Server-side injected authorization predicates enforcing user scope",
    )
    query_type: str = Field(
        ...,
        description="Analytical query category (e.g. METRIC_QUERY, BREAKDOWN_QUERY, COMPARISON_QUERY)",
    )
    limit: int = Field(
        default=100,
        description="Enforced maximum row count limit",
    )
    read_only: bool = Field(
        default=True,
        description="Strictly true for all generated institutional SQL artifacts",
    )
    validation_status: str = Field(
        default="VALID",
        description="AST security validation outcome",
    )
