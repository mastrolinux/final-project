"""
Admin Verification Endpoints

REST API endpoints for administrators to review, approve, and reject
context verification requests. The review unit is the context profile,
not the individual document. All endpoints require the ``require_admin``
dependency.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.dependencies.auth import require_admin
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.storage import StorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.verification_repository import VerificationRepository
from src.schemas.verification import (
    AdminContextVerificationDetail,
    AdminContextVerificationItem,
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
    context_repo = ContextRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return VerificationService(
        verification_repo=verification_repo,
        profile_repo=profile_repo,
        storage=storage,
        encryption=encryption,
        audit_service=audit_service,
        context_repo=context_repo,
    )


# ------------------------------------------------------------------
# List contexts pending verification
# ------------------------------------------------------------------


@router.get(
    "/verifications/contexts/pending",
    response_model=List[AdminContextVerificationItem],
)
async def list_pending_contexts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    List context profiles awaiting admin verification.

    Returns contexts in ``pending`` or ``under_review`` status that have
    at least one linked verification document, ordered by creation date
    (oldest first).
    """
    contexts = service.get_pending_contexts(limit=limit, offset=offset)

    items = []
    for ctx in contexts:
        display_name = None
        if ctx.base_profile and hasattr(ctx.base_profile, "display_name"):
            display_name = ctx.base_profile.display_name

        doc_count = 1 if ctx.document_id else 0

        items.append(
            AdminContextVerificationItem(
                context_id=ctx.id,
                context_type=ctx.context_type.value,
                context_name=ctx.context_name,
                display_name_override=ctx.display_name_override,
                email_override=ctx.email_override,
                verification_status=ctx.verification_status.value,
                user_id=ctx.user_id,
                user_display_name=display_name,
                document_count=doc_count,
                created_at=ctx.created_at,
            )
        )
    return items


# ------------------------------------------------------------------
# Get context details for review
# ------------------------------------------------------------------


@router.get(
    "/verifications/contexts/{context_id}",
    response_model=AdminContextVerificationDetail,
)
async def get_context_verification(
    context_id: UUID,
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Retrieve full context details with linked documents for admin review.

    Returns the context's identity claims alongside all linked documents,
    enabling the admin to compare document content against claimed fields.
    """
    try:
        ctx = service.get_context_for_review(context_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    # Fetch linked documents
    docs = service.verification_repo.get_documents_for_context(context_id)

    display_name = None
    if ctx.base_profile and hasattr(ctx.base_profile, "display_name"):
        display_name = ctx.base_profile.display_name

    return AdminContextVerificationDetail(
        context_id=ctx.id,
        context_type=ctx.context_type.value,
        context_name=ctx.context_name,
        display_name_override=ctx.display_name_override,
        email_override=ctx.email_override,
        phone_override=ctx.phone_override,
        bio=ctx.bio,
        verification_status=(
            ctx.verification_status.value if ctx.verification_status else "pending"
        ),
        rejection_reason=ctx.rejection_reason,
        user_id=ctx.user_id,
        user_display_name=display_name,
        documents=[
            VerificationDocumentResponse.model_validate(d) for d in docs
        ],
        created_at=ctx.created_at,
    )


# ------------------------------------------------------------------
# Review (approve / reject) context
# ------------------------------------------------------------------


@router.patch(
    "/verifications/contexts/{context_id}",
    response_model=AdminContextVerificationDetail,
)
async def review_context_verification(
    context_id: UUID,
    review: AdminVerificationReview,
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Approve or reject a context's verification request.

    When approving, the context is activated, the user's account type
    is promoted to ``verified``, and an optional document expiry date
    is set on all linked documents.

    When rejecting, the ``rejection_reason`` field is required and is
    stored on the context for the user to see.
    """
    try:
        updated_ctx = service.review_context(
            context_id=context_id,
            reviewer_id=admin.user_id,
            status=review.verification_status,
            reviewer_notes=review.reviewer_notes,
            document_expiry_date=review.document_expiry_date,
            rejection_reason=review.rejection_reason,
        )
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    # Build response with refreshed document list
    docs = service.verification_repo.get_documents_for_context(context_id)

    display_name = None
    if (
        updated_ctx.base_profile
        and hasattr(updated_ctx.base_profile, "display_name")
    ):
        display_name = updated_ctx.base_profile.display_name

    return AdminContextVerificationDetail(
        context_id=updated_ctx.id,
        context_type=updated_ctx.context_type.value,
        context_name=updated_ctx.context_name,
        display_name_override=updated_ctx.display_name_override,
        email_override=updated_ctx.email_override,
        phone_override=updated_ctx.phone_override,
        bio=updated_ctx.bio,
        verification_status=updated_ctx.verification_status.value,
        rejection_reason=updated_ctx.rejection_reason,
        user_id=updated_ctx.user_id,
        user_display_name=display_name,
        documents=[
            VerificationDocumentResponse.model_validate(d) for d in docs
        ],
        created_at=updated_ctx.created_at,
    )


# ------------------------------------------------------------------
# Download (decrypted document for admin review)
# ------------------------------------------------------------------


@router.get("/verifications/{document_id}/download")
async def download_verification_document(
    document_id: UUID,
    admin: AuthUser = Depends(require_admin),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Download and decrypt a verification document for review.

    Returns the original document bytes with appropriate content type
    and security headers to prevent caching and cross-origin attacks.
    """
    try:
        plaintext, content_type = service.download_document(
            document_id=document_id,
            admin_id=admin.user_id,
        )
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return Response(
        content=plaintext,
        media_type=content_type,
        headers={
            "Content-Disposition": "inline",
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
