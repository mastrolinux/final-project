"""
Admin User Management Endpoints

REST API endpoints for managing user accounts.
All endpoints require admin privileges.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.api.dependencies.auth import require_admin
from src.core.database import get_db
from src.models.audit import AuditEventType, AuditOperation
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.auth_repository import AuthRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.admin_users import (
    PurgeExpiredResponse,
    SoftDeletedUserListResponse,
    SoftDeletedUserResponse,
)
from src.services.audit_service import AuditService
from src.services.privacy_service import PrivacyService

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


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Dependency to get AuditService instance for admin audit logging."""
    return AuditService(AuditRepository(db))


@router.get(
    "/users/soft-deleted",
    response_model=SoftDeletedUserListResponse,
    summary="List Soft-Deleted Users",
    description=("List all soft-deleted user accounts with pagination. Requires admin privileges."),
)
def list_soft_deleted_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: AuthUser = Depends(require_admin),
    service: PrivacyService = Depends(get_privacy_service),
):
    """List all soft-deleted user accounts."""
    offset = (page - 1) * page_size
    users, total = service.list_soft_deleted_users(offset=offset, limit=page_size)
    return SoftDeletedUserListResponse(
        users=[
            SoftDeletedUserResponse(
                user_id=str(u.user_id),
                email=u.email,
                is_email_verified=u.is_email_verified,
                is_admin=u.is_admin,
                deleted_at=u.deleted_at,
                created_at=u.created_at,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/users/purge-expired",
    response_model=PurgeExpiredResponse,
    summary="Purge Expired Soft-Deleted Users",
    description=(
        "Permanently delete all soft-deleted user accounts whose 30-day "
        "retention period has expired. This is a destructive, irreversible "
        "operation. Requires admin privileges."
    ),
)
def purge_expired_users(
    request: Request,
    admin: AuthUser = Depends(require_admin),
    service: PrivacyService = Depends(get_privacy_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Purge all soft-deleted accounts past the retention period."""
    purged_count = service.purge_expired_accounts()

    audit_service.log_event(
        event_type=AuditEventType.account_permanently_purged,
        user_id=None,
        actor_id=admin.user_id,
        resource_type="account",
        resource_id="admin_purge_trigger",
        operation=AuditOperation.delete,
        changes={
            "admin_initiated": True,
            "purged_count": purged_count,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        legal_basis="gdpr_art_17_admin_purge",
    )

    return PurgeExpiredResponse(purged_count=purged_count)
