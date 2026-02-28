"""
Privacy API Endpoints

Provides GDPR-inspired privacy features:
- Article 15 data export
- Article 17 account deletion with 30-day retention
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_current_user, require_verified_user
from src.core.database import get_db
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.auth_repository import AuthRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.privacy import (
    DataExportResponse,
    DeletionRequestResponse,
    DeletionStatusResponse,
)
from src.services.audit_service import AuditService
from src.services.privacy_service import (
    AccountAlreadyDeletedError,
    PrivacyService,
    ProfileNotFoundError,
)

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


@router.post(
    "/deletion-request",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Account Deletion (GDPR Art. 17)",
    description=(
        "Soft-delete the authenticated user's account and all associated data. "
        "The account enters a 30-day grace period during which it can be restored "
        "by re-registering with the same email. After the grace period, "
        "data is permanently purged."
    ),
)
def request_deletion(
    request: Request,
    current_user: AuthUser = Depends(require_verified_user),
    service: PrivacyService = Depends(get_privacy_service),
):
    """Request account deletion with 30-day retention period."""
    try:
        result = service.soft_delete_account(
            user_id=current_user.user_id,
            actor_id=current_user.user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return DeletionRequestResponse(**result)
    except ProfileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    except AccountAlreadyDeletedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account is already scheduled for deletion",
        )


@router.get(
    "/deletion-status",
    response_model=DeletionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Deletion Status",
    description=(
        "Check the current deletion status of the authenticated user's account. "
        "Returns 'active', 'scheduled' (with dates), or 'purged'."
    ),
)
def get_deletion_status(
    current_user: AuthUser = Depends(get_current_user),
    service: PrivacyService = Depends(get_privacy_service),
):
    """Check account deletion status."""
    result = service.get_deletion_status(user_id=current_user.user_id)
    return DeletionStatusResponse(**result)
