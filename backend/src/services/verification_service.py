"""
Verification Service

Business logic for identity document upload, retrieval, and admin review.

Upload pipeline:
    1. Validate that the target profile exists
    2. Validate the document (magic bytes, size limit)
    3. Encrypt the document bytes with Fernet
    4. Upload the encrypted blob to the private storage bucket
    5. Persist document metadata in the database
    6. Record an audit event

Review pipeline (admin):
    1. Validate that the document exists and is in a reviewable state
    2. Transition the verification status to verified or rejected
    3. If verified, promote the user's account type to ``verified``
    4. Record an audit event with reviewer details
"""

import logging
import uuid as uuid_pkg
from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from src.core.document import DocumentValidationError, validate_document
from src.core.encryption import EncryptionError, EncryptionService
from src.core.storage import StorageClient
from src.models.audit import AuditEventType, AuditOperation
from src.models.profile import AccountType
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)
from src.repositories.profile_repository import ProfileRepository
from src.repositories.verification_repository import VerificationRepository
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class VerificationServiceError(Exception):
    """Domain exception for verification operations."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class VerificationService:
    """
    Orchestrates document upload, status queries, and admin review.

    Depends on:
        verification_repo  -- database access for verification_documents
        profile_repo       -- database access for base_profiles (account_type)
        storage            -- blob storage for encrypted documents
        encryption         -- Fernet encryption service
        audit_service      -- tamper-evident audit logging (optional)
    """

    def __init__(
        self,
        verification_repo: VerificationRepository,
        profile_repo: ProfileRepository,
        storage: StorageClient,
        encryption: EncryptionService,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self.verification_repo = verification_repo
        self.profile_repo = profile_repo
        self.storage = storage
        self.encryption = encryption
        self.audit_service = audit_service

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_document(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        claimed_content_type: str,
        document_type: DocumentType,
    ) -> VerificationDocument:
        """
        Validate, encrypt, store, and record a new verification document.

        Raises:
            VerificationServiceError: If the profile does not exist,
                the document fails validation, or storage/encryption fails.
        """
        # 1. Verify profile exists
        profile = self.profile_repo.get_profile_by_id(user_id)
        if profile is None:
            raise VerificationServiceError(
                f"Profile {user_id} not found", status_code=404
            )

        # 2. Validate document format and size
        try:
            detected_content_type = validate_document(
                file_data, claimed_content_type
            )
        except DocumentValidationError as exc:
            raise VerificationServiceError(str(exc)) from exc

        # 3. Encrypt
        try:
            encrypted_data = self.encryption.encrypt(file_data)
        except EncryptionError as exc:
            logger.error("Encryption failed for user %s: %s", user_id, exc)
            raise VerificationServiceError(
                "Document encryption failed", status_code=500
            ) from exc

        # 4. Upload to private bucket
        blob_id = str(uuid_pkg.uuid4())
        storage_path = f"{user_id}/{blob_id}/{filename}"
        try:
            result = self.storage.upload(
                storage_path, encrypted_data, "application/octet-stream"
            )
        except Exception as exc:
            logger.error("Storage upload failed for user %s: %s", user_id, exc)
            raise VerificationServiceError(
                "Document storage failed", status_code=500
            ) from exc

        # 5. Persist metadata
        doc = self.verification_repo.create_document(
            user_id=user_id,
            document_type=document_type,
            storage_path=result.storage_path,
            original_filename=filename,
            file_size_bytes=len(file_data),
            content_type=detected_content_type,
        )

        # 6. Audit
        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.document_upload,
                    user_id=user_id,
                    actor_id=user_id,
                    resource_type="verification_document",
                    resource_id=str(doc.id),
                    operation=AuditOperation.create,
                    changes={
                        "document_type": document_type.value,
                        "original_filename": filename,
                        "file_size_bytes": len(file_data),
                    },
                    legal_basis="consent",
                )
            except Exception:
                logger.warning(
                    "Audit logging failed for document upload %s",
                    doc.id,
                    exc_info=True,
                )

        logger.info(
            "Document uploaded: id=%s, user=%s, type=%s",
            doc.id, user_id, document_type.value,
        )
        return doc

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    def get_verification_status(self, user_id: UUID) -> Dict:
        """
        Return the user's current verification state.

        Includes account type, latest document (if any), and a derived
        boolean indicating whether the user can create legal/healthcare
        context profiles.
        """
        profile = self.profile_repo.get_profile_by_id(user_id)
        if profile is None:
            raise VerificationServiceError(
                f"Profile {user_id} not found", status_code=404
            )

        latest_doc = self.verification_repo.get_latest_user_document(user_id)

        return {
            "user_id": user_id,
            "account_type": profile.account_type,
            "latest_document": latest_doc,
            "can_create_legal_context": (
                profile.account_type == AccountType.verified
            ),
        }

    def get_user_documents(
        self, user_id: UUID
    ) -> List[VerificationDocument]:
        """Return all non-deleted documents for a user."""
        profile = self.profile_repo.get_profile_by_id(user_id)
        if profile is None:
            raise VerificationServiceError(
                f"Profile {user_id} not found", status_code=404
            )
        return self.verification_repo.get_user_documents(user_id)

    def get_document_by_id(
        self, document_id: UUID
    ) -> VerificationDocument:
        """Fetch a single document or raise."""
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )
        return doc

    # ------------------------------------------------------------------
    # Admin review
    # ------------------------------------------------------------------

    def get_pending_documents(
        self, limit: int = 50, offset: int = 0
    ) -> List[VerificationDocument]:
        """Return documents awaiting review (pending or under_review)."""
        return self.verification_repo.get_documents_by_status(
            statuses=[
                VerificationStatus.pending,
                VerificationStatus.under_review,
            ],
            limit=limit,
            offset=offset,
        )

    def review_document(
        self,
        document_id: UUID,
        reviewer_id: UUID,
        status: VerificationStatus,
        reviewer_notes: Optional[str] = None,
        document_expiry_date: Optional[date] = None,
        rejection_reason: Optional[str] = None,
    ) -> VerificationDocument:
        """
        Approve or reject a verification document.

        When approving, the user's account type is promoted to ``verified``.
        The document must be in a reviewable state (pending or under_review).

        Raises:
            VerificationServiceError: If the document does not exist,
                is not reviewable, or the target status is invalid.
        """
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )

        if not doc.is_reviewable:
            raise VerificationServiceError(
                f"Document {document_id} is in status "
                f"'{doc.verification_status.value}' and cannot be reviewed",
                status_code=409,
            )

        if status not in (
            VerificationStatus.verified,
            VerificationStatus.rejected,
        ):
            raise VerificationServiceError(
                "Review status must be 'verified' or 'rejected'"
            )

        if status == VerificationStatus.rejected and not rejection_reason:
            raise VerificationServiceError(
                "rejection_reason is required when rejecting a document"
            )

        # Transition status
        updated_doc = self.verification_repo.update_document_status(
            document_id=document_id,
            status=status,
            reviewer_id=reviewer_id,
            reviewer_notes=reviewer_notes,
            document_expiry_date=document_expiry_date,
            rejection_reason=rejection_reason,
        )

        # Promote account type on verification
        if status == VerificationStatus.verified:
            self.profile_repo.update_profile(
                doc.user_id, account_type=AccountType.verified
            )
            logger.info(
                "Account %s promoted to verified after document %s review",
                doc.user_id, document_id,
            )

        # Audit
        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.document_review,
                    user_id=doc.user_id,
                    actor_id=reviewer_id,
                    resource_type="verification_document",
                    resource_id=str(document_id),
                    operation=AuditOperation.review,
                    changes={
                        "status": status.value,
                        "reviewer_notes": reviewer_notes,
                        "document_expiry_date": (
                            str(document_expiry_date) if document_expiry_date else None
                        ),
                        "rejection_reason": rejection_reason,
                    },
                    legal_basis="legitimate_interest",
                )
            except Exception:
                logger.warning(
                    "Audit logging failed for document review %s",
                    document_id,
                    exc_info=True,
                )

        return updated_doc  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_document(
        self, document_id: UUID, actor_id: UUID
    ) -> bool:
        """
        Soft-delete a verification document and remove its encrypted blob.

        Returns True on success, raises on failure.
        """
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )

        # Remove encrypted blob from storage
        if doc.storage_path:
            try:
                self.storage.delete(doc.storage_path)
            except Exception:
                logger.warning(
                    "Failed to delete storage blob for document %s",
                    document_id,
                    exc_info=True,
                )

        result = self.verification_repo.soft_delete_document(document_id)

        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.document_delete,
                    user_id=doc.user_id,
                    actor_id=actor_id,
                    resource_type="verification_document",
                    resource_id=str(document_id),
                    operation=AuditOperation.delete,
                    legal_basis="consent",
                )
            except Exception:
                logger.warning(
                    "Audit logging failed for document delete %s",
                    document_id,
                    exc_info=True,
                )

        return result
