"""
Agent 63 – Top-Level API Router
Mounts versioned API routers under standardized prefixes.
"""

from fastapi import APIRouter
from backend.app.api.v1.router import api_v1_router

api_router = APIRouter()

# Mount /v1 subrouter (accessible as /api/v1/... when mounted under /api in main.py)
api_router.include_router(api_v1_router, prefix="/v1")
