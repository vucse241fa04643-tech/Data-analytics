"""
Agent 63 – API v1 Router
Aggregates all version 1 routes.
"""

from fastapi import APIRouter
from backend.app.api.v1 import health

api_v1_router = APIRouter()

# Health endpoints mounted at root of v1: /api/v1/health, /api/v1/health/ready
api_v1_router.include_router(health.router)
