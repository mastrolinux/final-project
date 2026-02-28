"""API v1 Router. Aggregates all endpoint routers."""

from fastapi import APIRouter

from src.api.v1.endpoints import (
    admin_oauth,
    admin_users,
    admin_verification,
    audit,
    auth,
    avatars,
    contexts,
    database,
    oauth,
    privacy,
    profiles,
    social_auth,
    verification,
)

api_router = APIRouter()


@api_router.get("/health")
async def api_health():
    """API v1 health check."""
    return {
        "status": "healthy",
        "api_version": "v1",
        "message": "API v1 is operational",
    }


# Database testing
api_router.include_router(database.router, prefix="/database", tags=["Database Testing"])
# Profiles
api_router.include_router(profiles.router, tags=["Profiles"])
# Contexts
api_router.include_router(contexts.router, tags=["Contexts"])
# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# Social authentication
api_router.include_router(social_auth.router, prefix="/auth", tags=["Social Authentication"])
# OAuth 2.1
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.1"])
# Admin - OAuth
api_router.include_router(admin_oauth.router, prefix="/admin/oauth", tags=["Admin - OAuth"])
# Admin - Users
api_router.include_router(admin_users.router, prefix="/admin", tags=["Admin - Users"])
# Audit
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
# Privacy
api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacy"])
# Avatars
api_router.include_router(avatars.router, tags=["Avatars"])
# Verification
api_router.include_router(verification.router, tags=["Verification"])
# Admin - Verification
api_router.include_router(admin_verification.router, prefix="/admin", tags=["Admin - Verification"])
