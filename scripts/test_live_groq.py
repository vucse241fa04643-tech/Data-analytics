"""
Agent 63 – Phase 6 Live Groq Provider Smoke Test
Performs exactly two targeted live requests using the configured GROQ_API_KEY.
Validates:
Query 1: 'What is the average attendance percentage for CSE students?'
Expected: Intent METRIC_QUERY, Metric attendance.percentage, Dimension department, Filter department=CSE

Query 2: 'Show active student strength by department.'
Expected: Intent BREAKDOWN_QUERY, Metric academics.active_student_strength, Dimension department
"""

import os
import sys
from dotenv import load_dotenv

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from backend.app.core.config import settings
from backend.app.schemas.intent import IntentRequest, IntentType, IntentValidationStatus
from backend.app.schemas.principal import (
    AuthenticatedPrincipal,
    ScopeType,
    ScopedRoleAssignment,
)
from backend.app.services.authorization import get_authorization_service
from backend.app.services.intent_llm_client import GroqIntentClient
from backend.app.services.intent_service import IntentService
from backend.app.services.intent_validator import IntentValidator
from backend.app.services.semantic_registry import get_semantic_registry_service


def run_live_tests():
    print("=" * 60)
    print("AGENT 63 – LIVE GROQ PROVIDER SMOKE TEST")
    print(f"Model: {settings.GROQ_MODEL}")
    print("GROQ_API_KEY is configured locally and is redacted from all output.")
    print("=" * 60)

    if not settings.is_groq_configured:
        print("[FAIL] GROQ_API_KEY is not configured in .env")
        sys.exit(1)

    client = GroqIntentClient()
    registry = get_semantic_registry_service()
    authz = get_authorization_service()
    validator = IntentValidator(registry)
    service = IntentService(
        llm_client=client,
        validator=validator,
        authorization_service=authz,
        semantic_registry=registry,
    )

    principal = AuthenticatedPrincipal(
        user_id="00000000-0000-0000-0000-000000000001",
        username="principal_director",
        email="principal@vignan.ac.in",
        roles=["PRINCIPAL"],
        scoped_roles=[ScopedRoleAssignment(role="PRINCIPAL", scope_type=ScopeType.INSTITUTION)],
        permissions={
            "analytics.read",
            "attendance.read",
            "assessment.read",
            "outcomes.read",
            "placement.read",
            "academics.read",
            "quality.read",
        },
    )

    # -------------------------------------------------------------
    # Live Query 1: Attendance
    # -------------------------------------------------------------
    q1 = "What is the average attendance percentage for CSE students?"
    print(f"\n[LIVE TEST 1] Submitting: \"{q1}\"")
    req1 = IntentRequest(message=q1)
    resp1 = service.interpret_intent(req1, principal)

    print(f"Status: {resp1.status.value}")
    if resp1.status != IntentValidationStatus.VALID or not resp1.intent:
        print(f"[FAIL] Query 1 validation failed: {resp1.message}")
        sys.exit(1)

    intent1 = resp1.intent
    print(f"Intent Type: {intent1.intent_type.value}")
    print(f"Metric ID:   {intent1.primary_metric_id}")
    print(f"Dimensions:  {intent1.dimensions}")
    print(f"Filters:     {intent1.filters}")

    assert intent1.intent_type == IntentType.METRIC_QUERY, f"Expected METRIC_QUERY, got {intent1.intent_type}"
    assert intent1.primary_metric_id == "attendance.percentage", f"Expected attendance.percentage, got {intent1.primary_metric_id}"
    assert "department" in intent1.dimensions or intent1.filters.get("department") == "CSE", "Expected department dimension or filter"
    assert intent1.filters.get("department") == "CSE", f"Expected filter department=CSE, got {intent1.filters}"
    print("[SUCCESS] Query 1 passed all verification criteria!")

    # -------------------------------------------------------------
    # Live Query 2: Active Student Strength Breakdown
    # -------------------------------------------------------------
    q2 = "Show active student strength by department."
    print(f"\n[LIVE TEST 2] Submitting: \"{q2}\"")
    req2 = IntentRequest(message=q2)
    resp2 = service.interpret_intent(req2, principal)

    print(f"Status: {resp2.status.value}")
    if resp2.status != IntentValidationStatus.VALID or not resp2.intent:
        print(f"[FAIL] Query 2 validation failed: {resp2.message}")
        sys.exit(1)

    intent2 = resp2.intent
    print(f"Intent Type: {intent2.intent_type.value}")
    print(f"Metric ID:   {intent2.primary_metric_id}")
    print(f"Dimensions:  {intent2.dimensions}")
    print(f"Filters:     {intent2.filters}")

    assert intent2.intent_type == IntentType.BREAKDOWN_QUERY, f"Expected BREAKDOWN_QUERY, got {intent2.intent_type}"
    assert intent2.primary_metric_id == "academics.active_student_strength", f"Expected academics.active_student_strength, got {intent2.primary_metric_id}"
    assert "department" in intent2.dimensions, f"Expected department dimension, got {intent2.dimensions}"
    print("[SUCCESS] Query 2 passed all verification criteria!")

    print("\n" + "=" * 60)
    print("ALL LIVE GROQ SMOKE TESTS COMPLETED SUCCESSFULLY (2/2)")
    print("=" * 60)


if __name__ == "__main__":
    run_live_tests()
