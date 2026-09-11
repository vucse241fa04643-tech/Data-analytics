"""
Agent 63 – Test Centralized Error Handling
Validates consistent JSON error schemas and verifies that internal stack traces,
SQL, and paths are not leaked to callers.
"""

from fastapi import APIRouter
from fastapi.testclient import TestClient
from backend.app.core.errors import AppException, ResourceNotFoundError
from backend.app.main import create_application


def test_standard_404_error_response_format(client: TestClient):
    """404 errors should return structured error object with request_id."""
    response = client.get("/api/v1/non_existent_endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    error = data["error"]
    assert error["code"] == "HTTP_404"
    assert error["message"] == "Not Found"
    assert "request_id" in error
    assert error["request_id"] is not None


def test_custom_app_exception_handling():
    """Domain exceptions are caught and formatted consistently."""
    test_app = create_application()
    test_router = APIRouter()

    @test_router.get("/trigger-app-error")
    def trigger_error():
        raise ResourceNotFoundError("Specific student record not found.")

    test_app.include_router(test_router)
    custom_client = TestClient(test_app)

    response = custom_client.get("/trigger-app-error")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["message"] == "Specific student record not found."
    assert "request_id" in data["error"]


def test_unhandled_exception_does_not_leak_stack_trace():
    """Unexpected runtime exceptions must return generic 500 without exposing Python tracebacks."""
    test_app = create_application()
    test_router = APIRouter()

    @test_router.get("/trigger-unhandled")
    def trigger_unhandled():
        # Raise unexpected error with sensitive-looking string
        raise ZeroDivisionError("division by zero at file /secret/internal/calc.py line 42")

    test_app.include_router(test_router)
    custom_client = TestClient(test_app, raise_server_exceptions=False)

    response = custom_client.get("/trigger-unhandled")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected internal server error occurred."
    
    # Assert no python traceback or path leakage in response
    body = response.text
    assert "Traceback" not in body
    assert "/secret/internal" not in body
    assert "ZeroDivisionError" not in body
