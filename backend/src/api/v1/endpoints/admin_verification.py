"""
Admin Verification Endpoints

REST API endpoints for administrators to review, approve, and reject
identity verification documents. All endpoints require the ``require_admin``
dependency.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies.auth import require_admin
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.storage import StorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.verification_repository import VerificationRepository
from src.schemas.verification import (
    AdminVerificationListItem,
    AdminVerificationReview,
    VerificationDocumentResponse,
)
from src.services.audit_service import AuditService
from src.services.verification_service import (
    VerificationService,
    VerificationServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_verification_service(
    db: Session = Depends(get_db),
    storage: StorageClient = Depends(get_document_storage_client),
    encryption: EncryptionService = Depends(get_encryption_service),
) -> VerificationService:
    """Dependency to build a VerificationService for admin operations."""
    verification_repo = VerificationRepository(db)
    profile_repo = ProfileRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return VerificationService(
        verification_repo=verification_repo,
        profile_repo=profile_repo,
        storage=storage,
        encryption=encryption,
        audit_service=audit_service,
    )


# ------------------------------------------------------------------
# List pending
# ------------------------------------------------------------------


@router.get(
    "/verifications/pending",
    response_model=List[AdminVerificationListItem],
)
async def list_pending_verifications(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    List verification documents awaiting admin review.

    Returns documents in ``pending`` or ``under_review`` status,
    ordered by submission date (oldest first).
    """
    docs = service.get_pending_documents(limit=limit, offset=offset)

    items = []
    for doc in docs:
        display_name = None
        if doc.user and hasattr(doc.user, "display_name"):
            display_name = doc.user.display_name
        items.append(
            AdminVerificationListItem(
                id=doc.id,
                user_id=doc.user_id,
                user_display_name=display_name,
                document_type=doc.document_type,
                verification_status=doc.verification_status,
                original_filename=doc.original_filename,
                file_size_bytes=doc.file_size_bytes,
                content_type=doc.content_type,
                created_at=doc.created_at,
            )
        )
    return items


# ------------------------------------------------------------------
# Get document details
# ------------------------------------------------------------------


@router.get(
    "/verifications/{document_id}",
    response_model=VerificationDocumentResponse,
)
async def get_verification_document(
    document_id: UUID,
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """Retrieve full metadata for a single verification document."""
    try:
        return service.get_document_by_id(document_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ------------------------------------------------------------------
# Review (approve / reject)
# ------------------------------------------------------------------


@router.patch(
    "/verifications/{document_id}",
    response_model=VerificationDocumentResponse,
)
async def review_verification_document(
    document_id: UUID,
    review: AdminVerificationReview,
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Approve or reject a verification document.

    When approving, the user's account type is promoted to ``verified``,
    enabling creation of legal and healthcare context profiles.

    The ``rejection_reason`` field is required when rejecting.
    """
    try:
        return service.review_document(
            document_id=document_id,
            reviewer_id=admin.user_id,
            status=review.verification_status,
            reviewer_notes=review.reviewer_notes,
            document_expiry_date=review.document_expiry_date,
            rejection_reason=review.rejection_reason,
        )
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
