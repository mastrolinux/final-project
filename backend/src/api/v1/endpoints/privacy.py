"""
Privacy API Endpoints

Provides GDPR Article 15 data export for authenticated users.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.api.dependencies.auth import get_current_user
from src.models.auth import AuthUser
from src.repositories.auth_repository import AuthRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.audit_repository import AuditRepository
from src.services.audit_service import AuditService
from src.services.privacy_service import PrivacyService, ProfileNotFoundError
from src.schemas.privacy import DataExportResponse

router = APIRouter()


def get_privacy_service(db: Session = Depends(get_db)) -> PrivacyService:
    """Dependency to get PrivacyService instance."""
    profile_repo = ProfileRepository(db)
    context_repo = ContextRepository(db)
    auth_repo = AuthRepository(db)
    oauth_repo = OAuthRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return PrivacyService(
        profile_repo=profile_repo,
        context_repo=context_repo,
        auth_repo=auth_repo,
        oauth_repo=oauth_repo,
        audit_service=audit_service,
    )


@router.get(
    "/export",
    response_model=DataExportResponse,
    summary="Export User Data (GDPR Art. 15)",
    description=(
        "Export all personal data held by the system for the authenticated user. "
        "Returns a machine-readable JSON document containing profile data, "
        "identity names, context profiles, authentication metadata, "
        "OAuth consents, and GDPR processing information."
    ),
)
def export_user_data(
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
):
    """Export all personal data for the authenticated user (GDPR Article 15)."""
    try:
        result = service.export_user_data(
            user_id=current_user.user_id,
            actor_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return result
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
