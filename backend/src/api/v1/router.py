"""
API v1 Router

Main router for API version 1.
Aggregates all endpoint routers for the v1 API.
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()


@api_router.get("/health")
async def api_health():
    """
    API v1 health check endpoint
    
    Returns API-specific health information.
    """
    return {
        "status": "healthy",
        "api_version": "v1",
        "message": "API v1 is operational",
    }


# Include database test endpoints
from src.api.v1.endpoints import database
api_router.include_router(database.router, prefix="/database", tags=["Database Testing"])

# Future endpoint routers will be included here:
# from src.api.v1.endpoints import auth, profiles, contexts, oauth, guardians, gdpr
# api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
# api_router.include_router(contexts.router, prefix="/contexts", tags=["Contexts"])
# api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.0"])
# api_router.include_router(guardians.router, prefix="/guardians", tags=["Guardians"])
# api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacy"])

