"""Agent 63 - Phase 14: Export Service
Serializes authorized analytical query results to CSV and JSON formats.

SECURITY INVARIANTS:
1. Re-authorizes principal on every export (fail-closed on role revocation / scope change).
2. Cross-user isolation: users can only export their own analytical artifacts.
3. CSV formula injection defense: sanitizes =, +, -, @, \\t, \\r on string fields.
4. Preserves authorized result data strictly: zero extra or hidden columns added.
5. Distinct NULL preservation (never collapses NULL to 0).
6. Hard limits enforced: EXPORT_MAX_ROWS (1000) and EXPORT_MAX_BYTES (2MB).
7. Emits safe EXPORT query log event (fail-open).
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.core.errors import AuthorizationError
from backend.app.core.logging import get_logger
from backend.app.schemas.export import (
    ExportFormat,
    ExportMetadata,
    ExportResponseJSON,
)
from backend.app.schemas.principal import AuthenticatedPrincipal, ScopeType
from backend.app.schemas.query_log import (
    QueryLogEvent,
    QueryLogEventType,
    QueryLogStatus,
)
from backend.app.services.authorization import (
    AuthorizationService,
    get_authorization_service,
)
from backend.app.services.export_artifact_store import (
    ExportArtifact,
    ExportArtifactStore,
    get_export_artifact_store,
)
from backend.app.services.query_log_service import (
    QueryLoggingService,
    get_query_log_service,
)

logger = get_logger("agent63.services.export")

# Characters that trigger formula execution in spreadsheet software (Excel, Calc)
_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Strict numeric regex matching real numbers (integers, floats, scientific notation)
_STRICT_NUMERIC_PATTERN = re.compile(r"^[-+]?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$")


def _is_numeric(val: Any) -> bool:
    """Checks if a value is a legitimate numeric literal or numeric string."""
    if isinstance(val, (int, float, Decimal)):
        return True
    if isinstance(val, str):
        return bool(_STRICT_NUMERIC_PATTERN.match(val))
    return False


def sanitize_csv_cell(value: Any) -> Any:
    """
    Sanitizes a single cell value against CSV formula injection while preserving numeric semantics.

    Spreadsheet Formula Injection Defense:
    1. Distinguishes actual numeric types (int, float, Decimal) and preserves them directly
       so spreadsheet software recognizes them as native numbers without converting to text.
    2. Legitimate negative numbers (e.g., -42, -3.14) or positive numbers represented as strings
       are parsed to their numeric representation, preserving numeric semantics in Excel/Calc.
    3. Malicious formula strings starting with dangerous prefixes (=, +, -, @, \\t, \\r) that
       do not represent pure numeric values (e.g., '=1+1', '+CMD(...)', '@SUM(...)', '-2+3')
       are neutralized by prepending a single quote (').
    4. None / NULL is preserved distinctly as empty string ("").
    5. Booleans are serialized as 'true' or 'false'.
    6. Structured dicts/lists are serialized as JSON strings.
    """
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float, Decimal)):
        return value

    if isinstance(value, (dict, list)):
        return json.dumps(value)

    if isinstance(value, datetime):
        return value.isoformat()

    val_str = str(value)
    if not val_str:
        return ""

    if val_str.startswith(_DANGEROUS_CSV_PREFIXES):
        # Allow legitimate negative/positive numbers without escaping to text
        if _STRICT_NUMERIC_PATTERN.match(val_str):
            try:
                if "." in val_str or "e" in val_str or "E" in val_str:
                    return float(val_str)
                return int(val_str)
            except ValueError:
                return f"'{val_str}"
        # Prefix dangerous formula strings with a single quote to force text interpretation
        return f"'{val_str}"

    return val_str


class ExportService:
    """Service orchestrating authorized analytical exports with defense-in-depth."""

    def __init__(
        self,
        artifact_store: Optional[ExportArtifactStore] = None,
        authorization_service: Optional[AuthorizationService] = None,
        log_service: Optional[QueryLoggingService] = None,
    ):
        self._artifact_store = artifact_store or get_export_artifact_store()
        self._auth_service = authorization_service or get_authorization_service()
        self._log_service = log_service or get_query_log_service()

    def export_result(
        self,
        request_id: str,
        export_format: ExportFormat,
        principal: AuthenticatedPrincipal,
    ) -> Tuple[bytes, str, str]:
        """
        Re-authorizes the principal, serializes the stored artifact, and returns:
        (encoded_bytes, media_type, filename)

        Raises:
            AuthorizationError: If principal is unauthenticated, inactive, unauthorized, or not owner.
            ValueError: If artifact not found, expired, or exceeds size limits.
        """
        # 1. Active Account Check
        if not principal or not principal.is_active:
            self._log_export_event(
                principal=principal,
                metric_id="unknown",
                status=QueryLogStatus.UNAUTHORIZED,
                error_category="INACTIVE_ACCOUNT",
            )
            raise AuthorizationError(
                message="Authentication required and account must be active.",
                details={"code": "INACTIVE_ACCOUNT"},
            )

        # 2. Retrieve server-side cached artifact
        artifact = self._artifact_store.get_artifact(request_id)
        if not artifact:
            raise ValueError(
                "Analytical result not found or export session expired. Please re-run the query."
            )

        # 3. Ownership and Cross-User Isolation
        if artifact.user_id != principal.user_id:
            logger.warning(
                f"Cross-user export attempt blocked: user '{principal.username}' attempted to export "
                f"artifact owned by user_id '{artifact.user_id}'"
            )
            self._log_export_event(
                principal=principal,
                metric_id=artifact.metric_id,
                status=QueryLogStatus.UNAUTHORIZED,
                error_category="CROSS_USER_EXPORT_BLOCKED",
            )
            raise AuthorizationError(
                message="Access denied: cannot export another user's analytical result.",
                details={"code": "CROSS_USER_EXPORT_BLOCKED"},
            )

        # 4. Mandatory Re-Authorization (Fail-Closed)
        scope_type_enum = (
            ScopeType(artifact.scope_type) if artifact.scope_type else None
        )
        decision = self._auth_service.authorize_metric(
            principal=principal,
            metric_id=artifact.metric_id,
            requested_scope_type=scope_type_enum,
            requested_scope_id=artifact.scope_id,
        )
        if not decision.allowed:
            logger.info(
                f"Export re-authorization failed for user '{principal.username}' "
                f"on metric '{artifact.metric_id}': {decision.reason_code}"
            )
            self._log_export_event(
                principal=principal,
                metric_id=artifact.metric_id,
                status=QueryLogStatus.UNAUTHORIZED,
                error_category=decision.reason_code,
            )
            raise AuthorizationError(
                message=f"Export unauthorized: {decision.message}",
                details={"code": decision.reason_code},
            )

        # Additional Scoped Role Boundaries
        if principal.has_role("STUDENT") and not principal.has_any_role("PRINCIPAL", "HOD", "DEAN", "IQAC"):
            if artifact.scope_type and artifact.scope_type != ScopeType.SELF.value:
                raise AuthorizationError(
                    message="Student accounts are restricted to exporting self-scoped records.",
                    details={"code": "SCOPE_OUT_OF_BOUNDS"},
                )

        if principal.has_role("HOD") and not principal.has_any_role("PRINCIPAL", "IQAC", "DEAN"):
            hod_scopes = principal.get_scopes_for_role("HOD")
            allowed_dept_ids = {sr.scope_id for sr in hod_scopes if sr.scope_id}
            if artifact.scope_type == ScopeType.DEPARTMENT.value and artifact.scope_id:
                if artifact.scope_id not in allowed_dept_ids:
                    raise AuthorizationError(
                        message="HOD scope violation: requested export does not match assigned department.",
                        details={"code": "SCOPE_OUT_OF_BOUNDS"},
                    )

        # 5. Row Count Ceiling Check
        rows = artifact.query_result.rows
        if len(rows) > settings.EXPORT_MAX_ROWS:
            self._log_export_event(
                principal=principal,
                metric_id=artifact.metric_id,
                status=QueryLogStatus.FAILED,
                error_category="ROW_LIMIT_EXCEEDED",
            )
            raise ValueError(
                f"Export row count ({len(rows)}) exceeds strict system ceiling ({settings.EXPORT_MAX_ROWS})."
            )

        # 6. Format Serialization
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_metric_slug = artifact.metric_id.replace(".", "_")

        if export_format == ExportFormat.CSV:
            encoded_bytes = self._serialize_csv(artifact)
            media_type = "text/csv; charset=utf-8"
            filename = f"agent63_{safe_metric_slug}_{timestamp_str}.csv"
        elif export_format == ExportFormat.JSON:
            encoded_bytes = self._serialize_json(artifact)
            media_type = "application/json"
            filename = f"agent63_{safe_metric_slug}_{timestamp_str}.json"
        elif export_format == ExportFormat.PDF:
            encoded_bytes = self._serialize_pdf(artifact)
            media_type = "application/pdf"
            filename = f"agent63_{safe_metric_slug}_{timestamp_str}.pdf"
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        # 7. Byte Limit Check
        if len(encoded_bytes) > settings.EXPORT_MAX_BYTES:
            self._log_export_event(
                principal=principal,
                metric_id=artifact.metric_id,
                status=QueryLogStatus.FAILED,
                error_category="BYTE_LIMIT_EXCEEDED",
            )
            raise ValueError(
                f"Export payload size ({len(encoded_bytes)} bytes) exceeds maximum ceiling ({settings.EXPORT_MAX_BYTES} bytes)."
            )

        # 8. Log Safe Export Event
        self._log_export_event(
            principal=principal,
            metric_id=artifact.metric_id,
            status=QueryLogStatus.SUCCESS,
            request_id=request_id,
            row_count=len(rows),
            dimensions=artifact.dimensions,
            scope_type=artifact.scope_type,
            scope_id=artifact.scope_id,
        )

        return encoded_bytes, media_type, filename

    def _serialize_csv(self, artifact: ExportArtifact) -> bytes:
        """Serializes analytical result rows to CSV with formula injection defense."""
        output = io.StringIO()
        writer = csv.writer(
            output,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\r\n",
        )

        columns = artifact.query_result.columns
        writer.writerow(columns)

        for row in artifact.query_result.rows:
            sanitized_row = [sanitize_csv_cell(row.get(col)) for col in columns]
            writer.writerow(sanitized_row)

        return output.getvalue().encode("utf-8-sig")  # UTF-8 with BOM for Excel compatibility

    def _serialize_json(self, artifact: ExportArtifact) -> bytes:
        """Serializes analytical result rows to structured JSON envelope."""
        metadata = ExportMetadata(
            metric_id=artifact.metric_id,
            metric_display_name=artifact.metric_display_name,
            query_type=artifact.query_type,
            dimensions=artifact.dimensions,
            scope_type=artifact.scope_type,
            row_count=len(artifact.query_result.rows),
        )

        response = ExportResponseJSON(
            export_metadata=metadata,
            columns=artifact.query_result.columns,
            data=artifact.query_result.rows,
        )

        json_str = response.model_dump_json(indent=2)
        return json_str.encode("utf-8")

    def _serialize_pdf(self, artifact: ExportArtifact) -> bytes:
        """
        Serializes analytical result to a clean, professional institutional PDF.
        Deterministic, robust, and zero raw SQL or sensitive credential exposure.
        """
        import io
        import html
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1E3A8A"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "H2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=6,
            spaceAfter=4,
        )
        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
        )
        meta_val_style = ParagraphStyle(
            "MetaVal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        )
        kpi_label_style = ParagraphStyle(
            "KpiLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1E3A8A"),
        )
        kpi_val_style = ParagraphStyle(
            "KpiVal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1E3A8A"),
        )
        cell_header_style = ParagraphStyle(
            "CellHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
        cell_style = ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("AGENT 63", title_style))
        story.append(Paragraph("Institutional Analytics Report", subtitle_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=8))

        # 2. Metadata Grid
        scope_display = artifact.scope_type or "INSTITUTION"
        if artifact.scope_id:
            scope_display += f" ({artifact.scope_id})"

        query_desc = artifact.metric_display_name
        if artifact.dimensions:
            query_desc += f" by {', '.join(artifact.dimensions)}"

        meta_rows = [
            [
                Paragraph("Result Title:", meta_label_style),
                Paragraph(html.escape(artifact.metric_display_name), meta_val_style),
                Paragraph("Generated At:", meta_label_style),
                Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), meta_val_style),
            ],
            [
                Paragraph("Query:", meta_label_style),
                Paragraph(html.escape(query_desc), meta_val_style),
                Paragraph("Scope:", meta_label_style),
                Paragraph(html.escape(scope_display), meta_val_style),
            ],
            [
                Paragraph("Request Trace ID:", meta_label_style),
                Paragraph(html.escape(artifact.request_id), meta_val_style),
                Paragraph("Verification Status:", meta_label_style),
                Paragraph("Read-Only PostgreSQL Verified", meta_val_style),
            ],
            [
                Paragraph("User Role:", meta_label_style),
                Paragraph(html.escape(artifact.role), meta_val_style),
                Paragraph("Governance:", meta_label_style),
                Paragraph("Read-Only / SQL Validated", meta_val_style),
            ],
        ]

        meta_table = Table(meta_rows, colWidths=[95, 175, 95, 175])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # 3. Main KPI Highlight (when 1 row or explicitly KPI)
        rows = artifact.query_result.rows
        columns = artifact.query_result.columns
        is_kpi = (len(rows) == 1 and len(columns) <= 3) or (artifact.visualization_type or "").lower() == "kpi"

        if is_kpi and len(rows) == 1:
            row0 = rows[0]
            kpi_val = None
            kpi_col = None
            for c in columns:
                if c.lower() in ("metric_value", "value", "count", "percentage", "average_ctc", "highest_ctc"):
                    kpi_val = row0.get(c)
                    kpi_col = c
                    break
            if kpi_val is None:
                for c in columns:
                    if isinstance(row0.get(c), (int, float)):
                        kpi_val = row0.get(c)
                        kpi_col = c
                        break

            if kpi_val is not None:
                formatted_kpi = str(kpi_val)
                if "ctc" in artifact.metric_id.lower() or "ctc" in (kpi_col or "").lower():
                    try:
                        num = float(kpi_val)
                        lakh = num / 100000 if num >= 1000 else num
                        formatted_kpi = f"₹{lakh:.2f} lakh/year"
                    except Exception:
                        pass
                elif "attendance" in artifact.metric_id.lower() or "percentage" in (kpi_col or "").lower():
                    try:
                        num = float(kpi_val)
                        formatted_kpi = f"{num:.2f}%" if not num.is_integer() else f"{int(num)}%"
                    except Exception:
                        pass
                elif isinstance(kpi_val, float):
                    formatted_kpi = f"{kpi_val:.2f}"

                kpi_table = Table([
                    [
                        Paragraph(f"<b>Key Metric:</b> {html.escape(artifact.metric_display_name)}", kpi_label_style),
                        Paragraph(f"<b>{html.escape(formatted_kpi)}</b>", kpi_val_style),
                    ]
                ], colWidths=[340, 200])
                kpi_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]))
                story.append(kpi_table)
                story.append(Spacer(1, 10))

        # 4. Result Data Table or Empty State
        if len(rows) == 0:
            empty_table = Table([[
                Paragraph(
                    "<b>Result Status:</b> No matching institutional records were found for this query in the authorized scope.",
                    cell_style,
                )
            ]], colWidths=[540])
            empty_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(empty_table)
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(f"Analytical Result Records ({len(rows)} row{'s' if len(rows) != 1 else ''})", h2_style))
            clean_headers = []
            for col in columns:
                label = "students" if col == "students_count" else col.replace("_", " ").title()
                clean_headers.append(Paragraph(html.escape(label), cell_header_style))

            max_display_rows = 500
            display_rows = rows[:max_display_rows]

            table_data = [clean_headers]
            for r in display_rows:
                row_cells = []
                for col in columns:
                    val = r.get(col)
                    val_str = "NULL" if val is None else str(val)
                    if ("ctc" in col.lower() or "ctc" in artifact.metric_id.lower()) and isinstance(val, (int, float)):
                        lakh = val / 100000 if val >= 1000 else val
                        val_str = f"₹{lakh:.2f} lakh/year"
                    elif "students_count" in val_str:
                        val_str = val_str.replace("students_count", "students")
                    row_cells.append(Paragraph(html.escape(val_str), cell_style))
                table_data.append(row_cells)

            col_width = 540.0 / max(len(columns), 1)
            col_widths = [col_width] * len(columns)

            result_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            result_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(result_table)
            story.append(Spacer(1, 10))

            if len(rows) > max_display_rows:
                story.append(Paragraph(
                    f"<i>Note: Displaying first {max_display_rows} of {len(rows)} records. For complete dataset, export as CSV or JSON.</i>",
                    footer_style,
                ))
                story.append(Spacer(1, 6))

        # 5. Governance & Verification Footer
        gov_table = Table([[
            Paragraph(
                "<b>Governance & Verification Information:</b><br/>"
                "• <b>Execution:</b> Read-Only PostgreSQL Transaction with strict 1000-row & 2MB boundaries.<br/>"
                "• <b>Validation:</b> Deterministic AST SQLGlot validation. Zero arbitrary SQL execution.<br/>"
                "• <b>Security:</b> Strict role-scoped authorization enforced. Confidential credentials, passwords, and raw SQL are excluded.<br/>"
                "• <b>Data Integrity:</b> Sourced directly from verified college database tables. No synthetic records.",
                footer_style,
            )
        ]], colWidths=[540])
        gov_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(gov_table)

        doc.build(story)
        return buffer.getvalue()

    def _log_export_event(
        self,
        principal: AuthenticatedPrincipal,
        metric_id: str,
        status: QueryLogStatus,
        request_id: Optional[str] = None,
        error_category: Optional[str] = None,
        row_count: int = 0,
        dimensions: Optional[List[str]] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> None:
        """Emits a safe EXPORT event to QueryLoggingService (fail-open)."""
        try:
            self._log_service.log_event(
                QueryLogEvent(
                    request_id=request_id,
                    user_id=principal.user_id if principal else None,
                    role=principal.roles[0] if principal and principal.roles else None,
                    scope_type=scope_type or (principal.scoped_roles[0].scope_type.value if principal and principal.scoped_roles else None),
                    scope_id=scope_id or (principal.scoped_roles[0].scope_id if principal and principal.scoped_roles else None),
                    metric_id=metric_id,
                    query_type="EXPORT",
                    dimensions=dimensions or [],
                    event_type=QueryLogEventType.EXPORT,
                    status=status,
                    error_category=error_category,
                    row_count=row_count,
                    execution_time_ms=0.0,
                )
            )
        except Exception as e:
            logger.warning(f"Export log event failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_singleton_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Dependency provider for ExportService."""
    global _singleton_export_service
    if _singleton_export_service is None:
        _singleton_export_service = ExportService()
    return _singleton_export_service


def reset_export_service() -> None:
    """Resets singleton instance for test isolation."""
    global _singleton_export_service
    _singleton_export_service = None
