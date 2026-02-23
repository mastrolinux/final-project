"""
Verification Service

Business logic for identity document upload, retrieval, context linking,
and admin review of context verification requests.

Upload pipeline:
    1. Validate that the target profile exists
    2. Validate the document (magic bytes, size limit)
    3. Encrypt the document bytes with Fernet
    4. Upload the encrypted blob to the private storage bucket
    5. Persist document metadata in the database
    6. Record an audit event

Context linking:
    Documents are linked to context profiles via a many-to-many join table.
    A single document (e.g. a passport) can verify multiple contexts, and
    each context can reference multiple supporting documents.

Review pipeline (admin):
    1. Validate that the context exists and is in a reviewable state
    2. Verify that the context has at least one linked document
    3. Transition the context's verification status to verified or rejected
    4. If verified, promote the user's account type to ``verified``
    5. Record an audit event with reviewer details
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
from src.models.context import ContextProfile
from src.models.profile import AccountType
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)
from src.repositories.context_repository import ContextRepository
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
    Orchestrates document upload, context linking, status queries,
    and admin context verification review.

    Depends on:
        verification_repo  -- database access for verification_documents
        profile_repo       -- database access for base_profiles (account_type)
        storage            -- blob storage for encrypted documents
        encryption         -- Fernet encryption service
        audit_service      -- tamper-evident audit logging (optional)
        context_repo       -- database access for context_profiles (optional)
    """

    def __init__(
        self,
        verification_repo: VerificationRepository,
        profile_repo: ProfileRepository,
        storage: Optional[StorageClient] = None,
        encryption: Optional[EncryptionService] = None,
        audit_service: Optional[AuditService] = None,
        context_repo: Optional[ContextRepository] = None,
    ) -> None:
        self.verification_repo = verification_repo
        self.profile_repo = profile_repo
        self.storage = storage
        self.encryption = encryption
        self.audit_service = audit_service
        self.context_repo = context_repo

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
        document_expiry_date: Optional[date] = None,
    ) -> VerificationDocument:
        """
        Validate, encrypt, store, and record a new verification document.

        Documents are uploaded as standalone entities. To associate a
        document with a context, call ``link_document_to_context`` after upload.

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
            document_expiry_date=document_expiry_date,
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
                        "document_expiry_date": (
                            str(document_expiry_date)
                            if document_expiry_date
                            else None
                        ),
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
    # Context-document linking
    # ------------------------------------------------------------------

    def link_document_to_context(
        self,
        user_id: UUID,
        context_id: UUID,
        document_id: UUID,
    ) -> VerificationDocument:
        """
        Link an existing document to a context profile.

        Validates that both the document and context belong to the user,
        the context requires verification (legal/healthcare), and the
        link does not already exist.

        Returns:
            The linked verification document.

        Raises:
            VerificationServiceError: On ownership, type, or duplicate errors.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )

        # Validate document
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )
        if str(doc.user_id) != str(user_id):
            raise VerificationServiceError(
                "Document does not belong to this user", status_code=403
            )

        # Validate context
        ctx = self.context_repo.get_context_profile_by_id(context_id)
        if ctx is None:
            raise VerificationServiceError(
                f"Context {context_id} not found", status_code=404
            )
        if str(ctx.user_id) != str(user_id):
            raise VerificationServiceError(
                "Context does not belong to this user", status_code=403
            )
        if not ctx.requires_verification:
            raise VerificationServiceError(
                f"Context type '{ctx.context_type.value}' does not require verification"
            )

        self.verification_repo.link_document_to_context(context_id, document_id)

        # Status transitions after document replacement:
        # - rejected  -> pending  (resubmit for re-review)
        # - verified  -> pending  (re-verification required, mirrors identity-change rule)
        # - under_review -> pending (document changed mid-review)
        # - pending   -> no change (document swapped, still awaiting review)
        if ctx.verification_status == VerificationStatus.rejected:
            self.context_repo.update_verification_status(
                context_id=context_id,
                verification_status=VerificationStatus.pending,
                is_active=False,
                rejection_reason=None,
            )
            logger.info(
                "Context %s resubmitted for verification (was rejected)",
                context_id,
            )
        elif ctx.verification_status == VerificationStatus.verified:
            self.context_repo.update_verification_status(
                context_id=context_id,
                verification_status=VerificationStatus.pending,
                is_active=False,
            )
            logger.info(
                "Context %s reset to pending (document replaced while verified)",
                context_id,
            )
        elif ctx.verification_status == VerificationStatus.under_review:
            self.context_repo.update_verification_status(
                context_id=context_id,
                verification_status=VerificationStatus.pending,
                is_active=False,
            )
            logger.info(
                "Context %s reset to pending (document replaced while under review)",
                context_id,
            )

        logger.info(
            "Document %s linked to context %s", document_id, context_id
        )
        return doc

    def unlink_document_from_context(
        self,
        user_id: UUID,
        context_id: UUID,
        document_id: UUID,
    ) -> None:
        """
        Remove the link between a document and a context profile.

        Raises:
            VerificationServiceError: On ownership errors or if the link
                does not exist.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )

        # Validate context ownership
        ctx = self.context_repo.get_context_profile_by_id(context_id)
        if ctx is None:
            raise VerificationServiceError(
                f"Context {context_id} not found", status_code=404
            )
        if str(ctx.user_id) != str(user_id):
            raise VerificationServiceError(
                "Context does not belong to this user", status_code=403
            )

        removed = self.verification_repo.unlink_document_from_context(
            context_id, document_id
        )
        if not removed:
            raise VerificationServiceError(
                "Document is not linked to this context", status_code=404
            )

        logger.info(
            "Document %s unlinked from context %s", document_id, context_id
        )

    def get_documents_for_context(
        self,
        user_id: UUID,
        context_id: UUID,
    ) -> List[VerificationDocument]:
        """
        Return all documents linked to a context profile.

        Validates that the context belongs to the requesting user.

        Raises:
            VerificationServiceError: If the context is not found
                or does not belong to the user.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )

        ctx = self.context_repo.get_context_profile_by_id(context_id)
        if ctx is None:
            raise VerificationServiceError(
                f"Context {context_id} not found", status_code=404
            )
        if str(ctx.user_id) != str(user_id):
            raise VerificationServiceError(
                "Context does not belong to this user", status_code=403
            )

        return self.verification_repo.get_documents_for_context(context_id)

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
    # Admin: pending contexts
    # ------------------------------------------------------------------

    def get_pending_contexts(
        self, limit: int = 50, offset: int = 0
    ) -> List[ContextProfile]:
        """Return contexts awaiting verification that have linked documents."""
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )
        return self.context_repo.get_contexts_pending_verification(
            limit=limit, offset=offset
        )

    def get_context_for_review(
        self, context_id: UUID
    ) -> ContextProfile:
        """
        Fetch a context profile for admin review, including its linked documents.

        Raises:
            VerificationServiceError: If the context is not found.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )
        ctx = self.context_repo.get_context_profile_by_id(context_id)
        if ctx is None:
            raise VerificationServiceError(
                f"Context {context_id} not found", status_code=404
            )
        return ctx

    # ------------------------------------------------------------------
    # Admin: context review
    # ------------------------------------------------------------------

    def review_context(
        self,
        context_id: UUID,
        reviewer_id: UUID,
        status: VerificationStatus,
        reviewer_notes: Optional[str] = None,
        document_expiry_date: Optional[date] = None,
        rejection_reason: Optional[str] = None,
    ) -> ContextProfile:
        """
        Approve or reject a context's verification request.

        When approving, the context is activated and the user's account
        type is promoted to ``verified``. When rejecting, the context
        remains inactive and the rejection reason is stored.

        Raises:
            VerificationServiceError: If the context does not exist,
                is not in a reviewable state, has no linked documents,
                or the target status is invalid.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )

        ctx = self.context_repo.get_context_profile_by_id(context_id)
        if ctx is None:
            raise VerificationServiceError(
                f"Context {context_id} not found", status_code=404
            )

        # Must be in a reviewable state
        if ctx.verification_status not in (
            VerificationStatus.pending,
            VerificationStatus.under_review,
        ):
            raise VerificationServiceError(
                f"Context is in status '{ctx.verification_status.value}' "
                f"and cannot be reviewed",
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
                "rejection_reason is required when rejecting"
            )

        # Verify at least one document is linked
        docs = self.verification_repo.get_documents_for_context(context_id)
        if not docs:
            raise VerificationServiceError(
                "Context has no linked verification documents",
                status_code=409,
            )

        # Transition context verification status
        if status == VerificationStatus.verified:
            updated_ctx = self.context_repo.update_verification_status(
                context_id=context_id,
                verification_status=VerificationStatus.verified,
                is_active=True,
                rejection_reason=None,
            )

            # Promote account type
            self.profile_repo.update_profile(
                ctx.user_id, account_type=AccountType.verified
            )
            logger.info(
                "Context %s verified, account %s promoted",
                context_id, ctx.user_id,
            )

            # Mark linked documents as verified
            for doc in docs:
                self.verification_repo.update_document_status(
                    document_id=UUID(str(doc.id)),
                    status=VerificationStatus.verified,
                    reviewer_id=reviewer_id,
                    reviewer_notes=reviewer_notes,
                    document_expiry_date=document_expiry_date,
                )

            # Send approval notification email
            profile = self.profile_repo.get_profile_by_id(ctx.user_id)
            if profile and profile.primary_email:
                try:
                    from src.tasks.email_tasks import send_approval_email

                    send_approval_email.delay(
                        profile.primary_email,
                        profile.legal_name or profile.primary_email,
                        ctx.context_name or ctx.context_type.value,
                    )
                except Exception:
                    logger.warning(
                        "Failed to queue approval email for context %s",
                        context_id,
                        exc_info=True,
                    )

        else:
            updated_ctx = self.context_repo.update_verification_status(
                context_id=context_id,
                verification_status=VerificationStatus.rejected,
                is_active=False,
                rejection_reason=rejection_reason,
            )

            # Propagate rejection to linked documents
            for doc in docs:
                self.verification_repo.update_document_status(
                    document_id=UUID(str(doc.id)),
                    status=VerificationStatus.rejected,
                    reviewer_id=reviewer_id,
                    reviewer_notes=reviewer_notes,
                    rejection_reason=rejection_reason,
                )

            # Send rejection notification email
            profile = self.profile_repo.get_profile_by_id(ctx.user_id)
            if profile and profile.primary_email:
                try:
                    from src.tasks.email_tasks import send_rejection_email

                    send_rejection_email.delay(
                        profile.primary_email,
                        profile.legal_name or profile.primary_email,
                        ctx.context_name or ctx.context_type.value,
                        rejection_reason,
                    )
                except Exception:
                    logger.warning(
                        "Failed to queue rejection email for context %s",
                        context_id,
                        exc_info=True,
                    )

        # Audit
        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.context_update,
                    user_id=ctx.user_id,
                    actor_id=reviewer_id,
                    resource_type="context_profile",
                    resource_id=str(context_id),
                    operation=AuditOperation.review,
                    changes={
                        "verification_status": status.value,
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
                    "Audit logging failed for context review %s",
                    context_id,
                    exc_info=True,
                )

        return updated_ctx  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Admin document download
    # ------------------------------------------------------------------

    def download_document(
        self,
        document_id: UUID,
        admin_id: UUID,
    ) -> tuple:
        """
        Download and decrypt a verification document for admin review.

        Pipeline: fetch metadata -> download encrypted blob -> decrypt -> audit.

        Args:
            document_id: Document ID to download
            admin_id: Admin user ID performing the download (for audit)

        Returns:
            Tuple of (plaintext_bytes, content_type)

        Raises:
            VerificationServiceError: If the document is not found,
                has no storage path, or decryption fails.
        """
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )

        if not doc.storage_path:
            raise VerificationServiceError(
                "Document has no associated file", status_code=404
            )

        # Download encrypted blob from private bucket
        try:
            encrypted_data = self.storage.download(doc.storage_path)
        except Exception as exc:
            logger.error(
                "Storage download failed for document %s: %s",
                document_id, exc,
            )
            raise VerificationServiceError(
                "Document download failed", status_code=500
            ) from exc

        # Decrypt
        try:
            plaintext = self.encryption.decrypt(encrypted_data)
        except EncryptionError as exc:
            logger.error(
                "Decryption failed for document %s: %s",
                document_id, exc,
            )
            raise VerificationServiceError(
                "Document decryption failed", status_code=500
            ) from exc

        # Audit the document view
        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.document_view,
                    user_id=doc.user_id,
                    actor_id=admin_id,
                    resource_type="verification_document",
                    resource_id=str(document_id),
                    operation=AuditOperation.read,
                    legal_basis="legitimate_interest",
                )
            except Exception:
                logger.warning(
                    "Audit logging failed for document view %s",
                    document_id,
                    exc_info=True,
                )

        return (plaintext, doc.content_type)

    # ------------------------------------------------------------------
    # Owner document download
    # ------------------------------------------------------------------

    def download_document_for_owner(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> tuple:
        """
        Download and decrypt a verification document for the owning user.

        Same decrypt pipeline as admin download but with ownership
        verification instead of admin authorization.

        Args:
            document_id: Document ID to download
            owner_id: User ID of the document owner

        Returns:
            Tuple of (plaintext_bytes, content_type)

        Raises:
            VerificationServiceError: If the document is not found,
                does not belong to the user, or decryption fails.
        """
        doc = self.verification_repo.get_document_by_id(document_id)
        if doc is None:
            raise VerificationServiceError(
                f"Document {document_id} not found", status_code=404
            )

        if str(doc.user_id) != str(owner_id):
            raise VerificationServiceError(
                "You can only download your own documents",
                status_code=403,
            )

        if not doc.storage_path:
            raise VerificationServiceError(
                "Document has no associated file", status_code=404
            )

        # Download encrypted blob from private bucket
        try:
            encrypted_data = self.storage.download(doc.storage_path)
        except Exception as exc:
            logger.error(
                "Storage download failed for document %s: %s",
                document_id, exc,
            )
            raise VerificationServiceError(
                "Document download failed", status_code=500
            ) from exc

        # Decrypt
        try:
            plaintext = self.encryption.decrypt(encrypted_data)
        except EncryptionError as exc:
            logger.error(
                "Decryption failed for document %s: %s",
                document_id, exc,
            )
            raise VerificationServiceError(
                "Document decryption failed", status_code=500
            ) from exc

        # Audit with user as both subject and actor
        if self.audit_service:
            try:
                self.audit_service.log_event(
                    event_type=AuditEventType.document_view,
                    user_id=owner_id,
                    actor_id=owner_id,
                    resource_type="verification_document",
                    resource_id=str(document_id),
                    operation=AuditOperation.read,
                    legal_basis="consent",
                )
            except Exception:
                logger.warning(
                    "Audit logging failed for document view %s",
                    document_id,
                    exc_info=True,
                )

        return (plaintext, doc.content_type)

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

    # ------------------------------------------------------------------
    # Automatic document expiry
    # ------------------------------------------------------------------

    def process_expired_documents(self) -> Dict:
        """
        Find all verified documents past their expiry date, deactivate
        linked contexts, mark documents as expired, send notifications,
        and log audit events.

        For each expired document the method:
        1. Deactivates all active contexts linked to the document
           (``is_active=False``, ``verification_status=pending``)
        2. Unlinks the document from each affected context
        3. Logs an audit event per deactivated context
        4. Marks the document as ``expired`` to prevent re-processing
        5. Sends a single notification email per user listing the
           affected context names

        Returns:
            Dict with ``expired_documents`` and ``deactivated_contexts``
            counts.

        Raises:
            VerificationServiceError: If context_repo is not configured.
        """
        if self.context_repo is None:
            raise VerificationServiceError(
                "Context repository not configured", status_code=500
            )

        expired_docs = (
            self.verification_repo.get_expired_verified_documents()
        )
        deactivated_count = 0

        for doc in expired_docs:
            contexts = self.context_repo.get_active_contexts_by_document_id(
                doc.id
            )

            for ctx in contexts:
                # Deactivate the context and reset to pending verification
                self.context_repo.update_verification_status(
                    context_id=ctx.id,
                    verification_status=VerificationStatus.pending,
                    is_active=False,
                )

                # Unlink the expired document
                self.verification_repo.unlink_document_from_context(
                    ctx.id, doc.id
                )
                deactivated_count += 1

                # Audit each deactivated context
                if self.audit_service:
                    try:
                        self.audit_service.log_event(
                            event_type=AuditEventType.document_expiry,
                            user_id=ctx.user_id,
                            actor_id=None,
                            resource_type="context_profile",
                            resource_id=str(ctx.id),
                            operation=AuditOperation.update,
                            changes={
                                "reason": "document_expired",
                                "document_id": str(doc.id),
                                "document_expiry_date": str(
                                    doc.document_expiry_date
                                ),
                                "previous_verification_status": (
                                    ctx.verification_status.value
                                    if ctx.verification_status
                                    else None
                                ),
                            },
                            legal_basis="legitimate_interest",
                        )
                    except Exception:
                        logger.warning(
                            "Audit logging failed for document expiry "
                            "context %s",
                            ctx.id,
                            exc_info=True,
                        )

                logger.info(
                    "Context %s deactivated: document %s expired on %s",
                    ctx.id, doc.id, doc.document_expiry_date,
                )

            # Mark the document as expired to prevent re-processing
            self.verification_repo.mark_document_expired(doc.id)

            # Send one notification email per user
            context_names = [
                c.context_name or c.context_type.value for c in contexts
            ]
            if context_names:
                profile = self.profile_repo.get_profile_by_id(doc.user_id)
                if profile and profile.primary_email:
                    try:
                        from src.tasks.email_tasks import (
                            send_document_expiry_email,
                        )

                        send_document_expiry_email.delay(
                            profile.primary_email,
                            profile.legal_name or profile.primary_email,
                            context_names,
                            str(doc.document_expiry_date),
                        )
                    except Exception:
                        logger.warning(
                            "Failed to queue expiry email for document %s",
                            doc.id,
                            exc_info=True,
                        )

        logger.info(
            "Document expiry check complete: %d documents, %d contexts "
            "deactivated",
            len(expired_docs), deactivated_count,
        )

        return {
            "expired_documents": len(expired_docs),
            "deactivated_contexts": deactivated_count,
        }
