"""
Avatar API Endpoints

REST API endpoints for uploading and deleting profile avatars.

Base avatar endpoints operate on the user's primary profile.
Context avatar endpoints allow per-context overrides that, when present,
take precedence over the base avatar in the inheritance engine.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.core.database import get_db
from src.core.storage import StorageClient, get_storage_client
from src.repositories.avatar_repository import AvatarRepository
from src.repositories.audit_repository import AuditRepository
from src.services.avatar_service import AvatarService, AvatarServiceError
from src.services.audit_service import AuditService
from src.schemas.avatar import AvatarResponse, AvatarDeleteResponse
from src.api.dependencies.auth import require_verified_user
from src.models.auth import AuthUser


router = APIRouter()


def get_avatar_service(
    db: Session = Depends(get_db),
    storage: StorageClient = Depends(get_storage_client),
) -> AvatarService:
    """Dependency to get AvatarService instance with audit logging."""
    avatar_repo = AvatarRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return AvatarService(avatar_repo, storage, audit_service=audit_service)


# ------------------------------------------------------------------
# Base profile avatar
# ------------------------------------------------------------------


@router.post(
    "/profiles/{user_id}/avatar",
    response_model=AvatarResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_base_avatar(
    user_id: UUID,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or WebP, max 5 MB)"),
    service: AvatarService = Depends(get_avatar_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """
    Upload or replace the base profile avatar.

    Accepts JPEG, PNG, or WebP images up to 5 MB. The image is center-cropped
    to a square, resized to 400x400 (avatar) and 80x80 (thumbnail), and
    converted to WebP format.
    """
    file_data = await file.read()
    logger.info("Avatar upload request: user_id=%s, file=%s, size=%d bytes",
                user_id, file.filename, len(file_data))
    try:
        result = service.upload_base_avatar(user_id, file_data)
        return result
    except AvatarServiceError as exc:
        logger.warning("Avatar upload rejected: %s", exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during avatar upload for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar upload failed: {exc}"
        )


@router.delete(
    "/profiles/{user_id}/avatar",
    response_model=AvatarDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_base_avatar(
    user_id: UUID,
    service: AvatarService = Depends(get_avatar_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """
    Delete the base profile avatar.

    Removes the stored image files and clears the avatar URLs from the profile.
    """
    try:
        result = service.delete_base_avatar(user_id)
        return result
    except AvatarServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ------------------------------------------------------------------
# Context profile avatar override
# ------------------------------------------------------------------


@router.post(
    "/profiles/{user_id}/contexts/{context_id}/avatar",
    response_model=AvatarResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_context_avatar(
    user_id: UUID,
    context_id: UUID,
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or WebP, max 5 MB)"),
    service: AvatarService = Depends(get_avatar_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """
    Upload or replace a context-specific avatar override.

    The context must belong to the given user. When a context override exists,
    it takes precedence over the base avatar in resolved profiles.
    """
    file_data = await file.read()
    try:
        result = service.upload_context_avatar(user_id, context_id, file_data)
        return result
    except AvatarServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.delete(
    "/profiles/{user_id}/contexts/{context_id}/avatar",
    response_model=AvatarDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_context_avatar(
    user_id: UUID,
    context_id: UUID,
    service: AvatarService = Depends(get_avatar_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """
    Delete a context-specific avatar override.

    After deletion, the resolved profile returns null for avatar fields.
    """
    try:
        result = service.delete_context_avatar(user_id, context_id)
        return result
    except AvatarServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
