"""Main router aggregator for API v1."""

from fastapi import APIRouter

# Import endpoint routers
from .endpoints import scoring, profile, resume, analysis

def create_v1_router() -> APIRouter:
    """Create and configure the v1 API router."""
    router = APIRouter(prefix="/api/v1")
    
    # Include all endpoint routers
    router.include_router(scoring.router)
    router.include_router(profile.router)
    router.include_router(resume.router)
    router.include_router(analysis.router)
    
    return router
