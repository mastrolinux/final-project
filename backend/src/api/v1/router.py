"""API v1 Router. Aggregates all endpoint routers."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
async def api_health():
    """API v1 health check."""
    return {
        "status": "healthy",
        "api_version": "v1",
        "message": "API v1 is operational",
    }


from src.api.v1.endpoints import database
api_router.include_router(database.router, prefix="/database", tags=["Database Testing"])

from src.api.v1.endpoints import profiles
api_router.include_router(profiles.router, tags=["Profiles"])

from src.api.v1.endpoints import contexts
api_router.include_router(contexts.router, tags=["Contexts"])

from src.api.v1.endpoints import auth
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

from src.api.v1.endpoints import social_auth
api_router.include_router(social_auth.router, prefix="/auth", tags=["Social Authentication"])

from src.api.v1.endpoints import oauth
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth 2.1"])

from src.api.v1.endpoints import admin_oauth
api_router.include_router(admin_oauth.router, prefix="/admin/oauth", tags=["Admin - OAuth"])

from src.api.v1.endpoints import admin_users
api_router.include_router(admin_users.router, prefix="/admin", tags=["Admin - Users"])

from src.api.v1.endpoints import audit
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])

from src.api.v1.endpoints import privacy
api_router.include_router(privacy.router, prefix="/privacy", tags=["Privacy"])

from src.api.v1.endpoints import avatars
api_router.include_router(avatars.router, tags=["Avatars"])

from src.api.v1.endpoints import verification
api_router.include_router(verification.router, tags=["Verification"])

from src.api.v1.endpoints import admin_verification
api_router.include_router(
    admin_verification.router, prefix="/admin", tags=["Admin - Verification"]
)

