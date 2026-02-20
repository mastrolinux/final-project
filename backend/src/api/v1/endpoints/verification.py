"""
Verification Document Endpoints (User-Facing)

REST API endpoints for uploading identity documents and checking
verification status. All endpoints require authentication and
enforce resource-owner authorization (users can only access their
own documents).
"""

import logging
from typing import List
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_current_user
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.storage import StorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.models.verification import DocumentType
from src.repositories.audit_repository import AuditRepository
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
# Upload
# ------------------------------------------------------------------


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
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Upload a government-issued identity document for verification.

    The document is validated (magic bytes, size), encrypted with Fernet,
    and stored in a private bucket. Only metadata is returned in the
    response; the encrypted content is never exposed via the API.
    """
    # Resource-owner check
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


# ------------------------------------------------------------------
# Status
# ------------------------------------------------------------------


@router.get(
    "/profiles/{user_id}/verification-status",
    response_model=VerificationStatusResponse,
)
async def get_verification_status(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """
    Return the user's current verification state.

    Includes account type, latest document metadata, and whether the
    user is eligible to create legal or healthcare context profiles.
    """
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own verification status",
        )

    try:
        return service.get_verification_status(user_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ------------------------------------------------------------------
# Document listing
# ------------------------------------------------------------------


@router.get(
    "/profiles/{user_id}/verification-documents",
    response_model=List[VerificationDocumentResponse],
)
async def list_verification_documents(
    user_id: UUID,
    current_user: AuthUser = Depends(get_current_user),
    service: VerificationService = Depends(get_verification_service),
):
    """
    List all verification documents for a user.

    Returns metadata only; encrypted document content is never included.
    """
    if str(current_user.user_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only list your own verification documents",
        )

    try:
        return service.get_user_documents(user_id)
    except VerificationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
