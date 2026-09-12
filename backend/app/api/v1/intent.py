"""
Agent 63 – Intent Interpretation API Endpoint
Accepts natural language analytical questions from authenticated users,
invokes Gemini for structured extraction, enforces semantic catalog validation,
and applies server-side authorization scoping.
"""

from fastapi import APIRouter, Depends, status

from backend.app.core.logging import get_logger, request_id_ctx_var
from backend.app.dependencies.auth import get_current_principal
from backend.app.schemas.intent import IntentRequest, IntentResponse
from backend.app.schemas.principal import AuthenticatedPrincipal
from backend.app.services.intent_service import (
    IntentService,
    get_intent_service,
)

logger = get_logger("agent63.api.intent")

router = APIRouter(prefix="/intent", tags=["Intent Interpretation"])


@router.post(
    "",
    response_model=IntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate natural language to structured analytical intent",
    description=(
        "Interprets an institutional analytics query into a grounded, validated, "
        "and authorized StructuredIntent object. Never executes SQL or accesses the database."
    ),
)
def interpret_query_intent(
    payload: IntentRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    intent_service: IntentService = Depends(get_intent_service),
) -> IntentResponse:
    """Interprets a natural language question into an authorized StructuredIntent."""
    req_id = request_id_ctx_var.get()
    return intent_service.interpret_intent(
        request=payload,
        principal=principal,
        request_id=req_id,
    )
