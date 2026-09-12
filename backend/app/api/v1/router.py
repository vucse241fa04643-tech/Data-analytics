"""
Agent 63 – API v1 Router
Aggregates all version 1 routes.
"""

from fastapi import APIRouter
from backend.app.api.v1 import health, auth, intent, agent

api_v1_router = APIRouter()

# Health endpoints mounted at root of v1: /api/v1/health, /api/v1/health/ready
api_v1_router.include_router(health.router)

# Auth endpoints mounted under /auth: /api/v1/auth/login, /api/v1/auth/me, /api/v1/auth/logout
api_v1_router.include_router(auth.router)

# Intent interpretation endpoints mounted under /intent: /api/v1/intent
api_v1_router.include_router(intent.router)

# Query execution endpoints mounted under /agent: /api/v1/agent/query
api_v1_router.include_router(agent.router)

