"""
Verification Document Endpoints (User-Facing)

REST API endpoints for uploading identity documents, checking
verification status, and managing context-document links.

All endpoints require authentication and enforce resource-owner
authorization (users can only access their own documents).
"""

import logging
from datetime import date
from typing import List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_current_user, require_verified_user
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.storage import StorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.models.verification import DocumentType
from src.repositories.audit_repository import AuditRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.verification_repository import VerificationRepository
from src.schemas.verification import (
    VerificationDocumentResponse,
    VerificationStatusResponse,
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
    """Dependency to build a VerificationService with all collaborators."""
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


#
# Upload
#


@router.post(
    "/profiles/{user_id}/verification-documents",
    response_model=VerificationDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_verification_document(
    user_id: UUID,
    file: UploadFile = File(
        ..., description="ID document file (PDF, JPEG, or PNG, max 10 MB)"
    ),
    document_type: DocumentType = Form(
        ..., description="Type of document: passport or national_id"
    ),
    document_expiry_date: date = Form(
        ..., description="Physical document expiry date (YYYY-MM-DD)"
    ),
    current_user: AuthUser = Depends(require_verified_user),
    service: VerificationService = Depends(get_verification_service),
):
    """Upload a government-issued identity document for verification."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only upload documents for your own profile",
        )

    file_data = await file.read()
    logger.info(
        "Document upload request: user_id=%s, file=%s, type=%s, size=%d bytes",
        user_id, file.filename, document_type.value, len(file_data),
    )

    try:
        doc = service.upload_document(
            user_id=user_id,
            file_data=file_data,
            filename=file.filename or "document",
            claimed_content_type=file.content_type or "",
            document_type=document_type,
            document_expiry_date=document_expiry_date,
        )
        return doc
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception(
            "Unexpected error during document upload for user %s", user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {exc}",
        )


#
# Status
#


@router.get(
    "/profiles/{user_id}/verification-status",
    response_model=VerificationStatusResponse,
)
async def get_verification_status(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """Return the user's current verification state."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own verification status",
        )

    try:
        return service.get_verification_status(user_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


#
# Document listing
#


@router.get(
    "/profiles/{user_id}/verification-documents",
    response_model=List[VerificationDocumentResponse],
)
async def list_verification_documents(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """List all verification documents for a user (metadata only)."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only list your own verification documents",
        )

    try:
        return service.get_user_documents(user_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


#
# Document download (decrypted for the owning user)
#


@router.get(
    "/profiles/{user_id}/verification-documents/{document_id}/download",
)
async def download_own_document(
    user_id: UUID,
    document_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """Download and decrypt an owned verification document."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only download your own documents",
        )

    try:
        plaintext, content_type = service.download_document_for_owner(
            document_id=document_id,
            owner_id=user_id,
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


#
# Context-document linking
#


@router.get(
    "/profiles/{user_id}/contexts/{context_id}/documents",
    response_model=List[VerificationDocumentResponse],
)
async def list_context_documents(
    user_id: UUID,
    context_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """List all verification documents linked to a context profile."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own documents",
        )

    try:
        return service.get_documents_for_context(user_id, context_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/profiles/{user_id}/contexts/{context_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def link_document_to_context(
    user_id: UUID,
    context_id: UUID,
    document_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """Link a verification document to a context profile."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only link your own documents",
        )

    try:
        service.link_document_to_context(user_id, context_id, document_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.delete(
    "/profiles/{user_id}/contexts/{context_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_document_from_context(
    user_id: UUID,
    context_id: UUID,
    document_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """Remove the link between a verification document and a context profile."""
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only unlink your own documents",
        )

    try:
        service.unlink_document_from_context(user_id, context_id, document_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
