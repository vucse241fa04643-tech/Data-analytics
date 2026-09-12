"""Agent 63 - Phase 12: Dashboard Definition Registry
Authoritative server-controlled definitions of role-based institutional dashboards.

CRITICAL SECURITY INVARIANTS:
- Defines strictly which approved semantic metrics, dimensions, and visual layouts are assigned to each role.
- Never contains raw SQL.
- Contains NO mock or synthetic institutional data.
- Does not grant authorization: backend AuthorizationService validates the user's role and scope per widget.
"""

from typing import Dict, List, Optional

from backend.app.schemas.dashboard import (
    DashboardDefinition,
    WidgetDefinition,
    WidgetRefreshPolicy,
    WidgetVisualizationType,
)

# -------------------------------------------------------------------------
# Server-Controlled Dashboard Definitions
# -------------------------------------------------------------------------

DASHBOARD_REGISTRY: Dict[str, DashboardDefinition] = {
    # 1. Principal / Executive Leadership Dashboard
    "principal_executive": DashboardDefinition(
        dashboard_id="principal_executive",
        title="Principal Institutional Overview",
        description="Executive institutional-wide dashboard monitoring core academic, attendance, placement, and quality metrics.",
        allowed_roles=["PRINCIPAL", "ADMIN"],
        default_role="PRINCIPAL",
        widgets=[
            WidgetDefinition(
                widget_id="prin_active_strength",
                metric_id="academics.active_student_strength",
                title="Total Enrolled Students",
                description="Total active student enrollment across all campus programmes.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="prin_attendance_pct",
                metric_id="attendance.percentage",
                title="Institutional Attendance Rate",
                description="Aggregated campus-wide attendance percentage across all active offerings.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="prin_dept_pass_rate",
                metric_id="assessment.course_pass_percentage",
                title="Departmental Course Pass Rates",
                description="Comparative course pass rate distribution across academic departments.",
                visualization_type=WidgetVisualizationType.BAR_CHART,
                dimension="dim.department",
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="prin_placed_count",
                metric_id="placement.placed_students_count",
                title="Graduating Students Placed",
                description="Total students placed in campus recruitment cycles.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="prin_avg_ctc",
                metric_id="placement.average_ctc",
                title="Average Placement Package (LPA)",
                description="Average annual cost-to-company offered across participating companies.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
            WidgetDefinition(
                widget_id="prin_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="Departmental CO Attainment",
                description="Average course outcome attainment level on a 3-point scale by department.",
                visualization_type=WidgetVisualizationType.BAR_CHART,
                dimension="dim.department",
                display_order=6,
            ),
            WidgetDefinition(
                widget_id="prin_quality_kpi",
                metric_id="quality.kpi_latest_value",
                title="Accreditation Quality Index",
                description="Institutional quality KPI score evaluated against academic benchmarks.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=7,
            ),
        ],
    ),

    # 2. Dean / Campus Leadership Dashboard
    "dean_campus": DashboardDefinition(
        dashboard_id="dean_campus",
        title="Dean Campus & Academic Dashboard",
        description="Campus-level analytics covering student strength, pass rates, and outcome attainment.",
        allowed_roles=["DEAN", "PRINCIPAL"],
        default_role="DEAN",
        widgets=[
            WidgetDefinition(
                widget_id="dean_student_strength",
                metric_id="academics.active_student_strength",
                title="Campus Student Strength",
                description="Total active enrolled students within the dean's campus scope.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="dean_attendance_rate",
                metric_id="attendance.percentage",
                title="Campus Average Attendance",
                description="Average attendance percentage across campus offerings.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="dean_dept_pass_rates",
                metric_id="assessment.course_pass_percentage",
                title="Departmental Pass Percentage",
                description="Pass rate breakdown by academic department.",
                visualization_type=WidgetVisualizationType.BAR_CHART,
                dimension="dim.department",
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="dean_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="Overall CO Attainment Level",
                description="Average outcome attainment across campus courses.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="dean_active_offerings",
                metric_id="academics.active_course_offerings",
                title="Active Course Offerings",
                description="Total ongoing instructional course offerings this term.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
        ],
    ),

    # 3. Head of Department (HOD) Dashboard
    "hod_department": DashboardDefinition(
        dashboard_id="hod_department",
        title="Departmental Operations Dashboard",
        description="Department-scoped analytics monitoring student attendance, exam performance, and outcome attainment.",
        allowed_roles=["HOD"],
        default_role="HOD",
        widgets=[
            WidgetDefinition(
                widget_id="hod_attendance_pct",
                metric_id="attendance.percentage",
                title="Department Attendance Rate",
                description="Average attendance percentage for departmental course offerings.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="hod_shortage_count",
                metric_id="attendance.shortage_count",
                title="Students with Attendance Shortage",
                description="Number of students below the 75% attendance threshold.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="hod_pass_percentage",
                metric_id="assessment.course_pass_percentage",
                title="Course Pass Rate Trend",
                description="Course pass percentage evaluated across academic years.",
                visualization_type=WidgetVisualizationType.BAR_CHART,
                dimension="dim.academic_year",
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="hod_avg_marks",
                metric_id="assessment.average_total_marks",
                title="Department Average Marks",
                description="Average assessment marks attained across departmental courses.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="hod_failure_count",
                metric_id="assessment.failure_count",
                title="Course Failure Count",
                description="Total course failures recorded in departmental exams.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
            WidgetDefinition(
                widget_id="hod_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="Department CO Attainment",
                description="Course outcome attainment score within the department.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=6,
            ),
        ],
    ),

    # 4. Faculty Academic Dashboard
    "faculty_academic": DashboardDefinition(
        dashboard_id="faculty_academic",
        title="Faculty Instructional Dashboard",
        description="Course-offering scoped analytics for assigned instructional sections and courses.",
        allowed_roles=["FACULTY"],
        default_role="FACULTY",
        widgets=[
            WidgetDefinition(
                widget_id="fac_offering_attendance",
                metric_id="attendance.percentage",
                title="Offering Attendance Percentage",
                description="Average attendance percentage in the faculty's assigned course offering.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="fac_offering_pass_rate",
                metric_id="assessment.course_pass_percentage",
                title="Course Pass Rate",
                description="Percentage of students passing the assigned course offering.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="fac_offering_avg_marks",
                metric_id="assessment.average_total_marks",
                title="Offering Average Marks",
                description="Mean total marks attained in the faculty's sections.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="fac_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="Course Outcome Attainment Level",
                description="Direct assessment CO attainment level for the assigned course.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
        ],
    ),

    # 5. IQAC / Accreditation Dashboard
    "iqac_quality": DashboardDefinition(
        dashboard_id="iqac_quality",
        title="IQAC Quality & Accreditation Dashboard",
        description="Institutional quality indicators, KPI target variances, and CO/PO outcome attainment distributions.",
        allowed_roles=["IQAC", "PRINCIPAL"],
        default_role="IQAC",
        widgets=[
            WidgetDefinition(
                widget_id="iqac_latest_kpi",
                metric_id="quality.kpi_latest_value",
                title="Quality KPI Latest Value",
                description="Institutional quality metrics evaluated against institutional targets.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="iqac_target_variance",
                metric_id="quality.kpi_target_variance",
                title="Quality KPI Target Variance",
                description="Percentage variance between observed performance and institutional targets.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="iqac_dept_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="CO Attainment by Department",
                description="Cross-departmental course outcome attainment distribution.",
                visualization_type=WidgetVisualizationType.BAR_CHART,
                dimension="dim.department",
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="iqac_po_attainment",
                metric_id="outcomes.po_attainment_level",
                title="Programme Outcome (PO) Attainment",
                description="Overall programme outcome attainment average across departments.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="iqac_attendance_avg",
                metric_id="attendance.percentage",
                title="Institutional Attendance Average",
                description="Campus-wide student attendance aggregate.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
            WidgetDefinition(
                widget_id="iqac_pass_rate_avg",
                metric_id="assessment.course_pass_percentage",
                title="Institutional Pass Rate",
                description="Overall student pass rate across all evaluated courses.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=6,
            ),
        ],
    ),

    # 6. Placement Officer Dashboard
    "placement_executive": DashboardDefinition(
        dashboard_id="placement_executive",
        title="Placement & Career Analytics Dashboard",
        description="Placement statistics, job offers, salary packages, and student readiness metrics.",
        allowed_roles=["PLACEMENT", "PRINCIPAL"],
        default_role="PLACEMENT",
        widgets=[
            WidgetDefinition(
                widget_id="place_placed_count",
                metric_id="placement.placed_students_count",
                title="Total Placed Students",
                description="Count of distinct eligible students placed in campus drives.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="place_offers_count",
                metric_id="placement.total_offers_count",
                title="Total Placement Offers",
                description="Total job offers extended by recruiting companies.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="place_avg_ctc",
                metric_id="placement.average_ctc",
                title="Average Package (LPA)",
                description="Mean annual CTC offered across placed cohorts.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="place_highest_ctc",
                metric_id="placement.highest_ctc",
                title="Highest Package (LPA)",
                description="Maximum annual CTC secured by a student in the current cycle.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="place_readiness_score",
                metric_id="placement.readiness_average_score",
                title="Placement Readiness Index",
                description="Average student readiness assessment score.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
        ],
    ),

    # 7. Controller of Examinations (COE) Dashboard
    "coe_examination": DashboardDefinition(
        dashboard_id="coe_examination",
        title="Examination & Evaluation Dashboard",
        description="Institutional examination pass rates, candidate counts, and outcome achievements.",
        allowed_roles=["COE", "PRINCIPAL"],
        default_role="COE",
        widgets=[
            WidgetDefinition(
                widget_id="coe_pass_percentage",
                metric_id="assessment.course_pass_percentage",
                title="Examination Pass Rate",
                description="Aggregated course pass percentage across all conducted examinations.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="coe_students_appeared",
                metric_id="assessment.students_appeared",
                title="Total Candidates Appeared",
                description="Total examinees recorded across scheduled institutional exams.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="coe_students_passed",
                metric_id="assessment.students_passed",
                title="Candidates Passed",
                description="Total examinees securing passing grades.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=3,
            ),
            WidgetDefinition(
                widget_id="coe_failure_count",
                metric_id="assessment.failure_count",
                title="Total Course Failures",
                description="Total course-level exam failure incidents.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=4,
            ),
            WidgetDefinition(
                widget_id="coe_co_attainment",
                metric_id="outcomes.co_attainment_level",
                title="Outcome Attainment Level",
                description="Average course outcome attainment recorded from examinations.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=5,
            ),
        ],
    ),

    # 8. Mentor Dashboard
    "mentor_mentees": DashboardDefinition(
        dashboard_id="mentor_mentees",
        title="Mentee Advisory Dashboard",
        description="Academic and attendance tracking scoped strictly to assigned mentee students.",
        allowed_roles=["MENTOR"],
        default_role="MENTOR",
        widgets=[
            WidgetDefinition(
                widget_id="mentor_mentee_attendance",
                metric_id="attendance.percentage",
                title="Mentee Attendance Rate",
                description="Average attendance percentage across assigned mentee students.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="mentor_mentee_pass_rate",
                metric_id="assessment.course_pass_percentage",
                title="Mentee Course Pass Rate",
                description="Pass rate percentage across courses taken by mentees.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
        ],
    ),

    # 9. Student Dashboard
    "student_self": DashboardDefinition(
        dashboard_id="student_self",
        title="My Student Academic Dashboard",
        description="Personal student academic progress, attendance percentage, and outcome attainment.",
        allowed_roles=["STUDENT"],
        default_role="STUDENT",
        widgets=[
            WidgetDefinition(
                widget_id="student_my_attendance",
                metric_id="attendance.percentage",
                title="My Overall Attendance",
                description="My current attendance percentage across enrolled courses.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=1,
            ),
            WidgetDefinition(
                widget_id="student_my_pass_rate",
                metric_id="assessment.course_pass_percentage",
                title="My Course Pass Percentage",
                description="Percentage of enrolled courses successfully passed.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=2,
            ),
            WidgetDefinition(
                widget_id="student_my_attainment",
                metric_id="outcomes.co_attainment_level",
                title="My Outcome Attainment",
                description="My average course outcome attainment level.",
                visualization_type=WidgetVisualizationType.KPI,
                display_order=3,
            ),
        ],
    ),
}


class DashboardRegistryService:
    """Provides server-controlled dashboard lookup and role-to-dashboard catalog resolution."""

    def __init__(self, registry: Optional[Dict[str, DashboardDefinition]] = None):
        self._registry = registry if registry is not None else DASHBOARD_REGISTRY

    def get_dashboard_definition(self, dashboard_id: str) -> Optional[DashboardDefinition]:
        """Retrieves a dashboard definition by its unique identifier."""
        return self._registry.get(dashboard_id)

    def get_dashboards_for_role(self, role: str) -> List[DashboardDefinition]:
        """Returns all dashboard definitions permitted for a specific institutional role."""
        normalized_role = role.upper()
        return [
            defn for defn in self._registry.values()
            if normalized_role in [r.upper() for r in defn.allowed_roles]
        ]

    def get_dashboards_for_roles(self, roles: List[str]) -> List[DashboardDefinition]:
        """Returns all distinct dashboard definitions permitted for any of the user's roles."""
        user_roles = {r.upper() for r in roles}
        matched: List[DashboardDefinition] = []
        seen_ids = set()

        for defn in self._registry.values():
            if defn.dashboard_id in seen_ids:
                continue
            defn_roles = {r.upper() for r in defn.allowed_roles}
            if user_roles & defn_roles:
                matched.append(defn)
                seen_ids.add(defn.dashboard_id)

        return matched

    def get_all_definitions(self) -> Dict[str, DashboardDefinition]:
        """Returns the full dictionary of configured dashboards."""
        return dict(self._registry)


_singleton_dashboard_registry: Optional[DashboardRegistryService] = None


def get_dashboard_registry_service() -> DashboardRegistryService:
    """Dependency provider for DashboardRegistryService."""
    global _singleton_dashboard_registry
    if _singleton_dashboard_registry is None:
        _singleton_dashboard_registry = DashboardRegistryService()
    return _singleton_dashboard_registry
