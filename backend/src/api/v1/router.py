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

# Include profile endpoints
from src.api.v1.endpoints import profiles
api_router.include_router(profiles.router, tags=["Profiles"])

# Include context endpoints
from src.api.v1.endpoints import contexts
api_router.include_router(contexts.router, tags=["Contexts"])

# Include auth endpoints
from src.api.v1.endpoints import auth
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include OAuth 2.1 endpoints
from src.api.v1.endpoints import oauth
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.1"])

# Future endpoint routers will be included here:
# from src.api.v1.endpoints import guardians, privacy
# api_router.include_router(guardians.router, prefix="/guardians", tags=["Guardians"])
# api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacy"])

