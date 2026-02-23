"""
Verification Document Repository

Data access layer for verification_documents table.
All queries exclude soft-deleted records unless explicitly requested.
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.models.context import ContextProfile
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class VerificationRepository:
    """CRUD operations for verification documents."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_document(
        self,
        user_id: UUID,
        document_type: DocumentType,
        storage_path: str,
        original_filename: str,
        file_size_bytes: int,
        content_type: str,
        document_expiry_date: Optional[date] = None,
    ) -> VerificationDocument:
        """Persist a new verification document with status ``pending``."""
        doc = VerificationDocument(
            user_id=str(user_id),
            document_type=document_type,
            verification_status=VerificationStatus.pending,
            storage_path=storage_path,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            content_type=content_type,
            document_expiry_date=document_expiry_date,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_document_by_id(
        self, document_id: UUID
    ) -> Optional[VerificationDocument]:
        """Fetch a single document by primary key, excluding soft-deleted."""
        return (
            self.db.query(VerificationDocument)
            .filter(
                and_(
                    VerificationDocument.id == str(document_id),
                    VerificationDocument.deleted_at.is_(None),
                )
            )
            .first()
        )

    def get_user_documents(
        self, user_id: UUID
    ) -> List[VerificationDocument]:
        """Return all non-deleted documents for a user, newest first."""
        return (
            self.db.query(VerificationDocument)
            .filter(
                and_(
                    VerificationDocument.user_id == str(user_id),
                    VerificationDocument.deleted_at.is_(None),
                )
            )
            .order_by(VerificationDocument.created_at.desc())
            .all()
        )

    def get_latest_user_document(
        self, user_id: UUID
    ) -> Optional[VerificationDocument]:
        """Return the most recently created non-deleted document for a user."""
        return (
            self.db.query(VerificationDocument)
            .filter(
                and_(
                    VerificationDocument.user_id == str(user_id),
                    VerificationDocument.deleted_at.is_(None),
                )
            )
            .order_by(VerificationDocument.created_at.desc())
            .first()
        )

    def get_documents_by_status(
        self,
        statuses: List[VerificationStatus],
        limit: int = 50,
        offset: int = 0,
    ) -> List[VerificationDocument]:
        """Return documents matching any of the given statuses (paginated)."""
        return (
            self.db.query(VerificationDocument)
            .filter(
                and_(
                    VerificationDocument.verification_status.in_(statuses),
                    VerificationDocument.deleted_at.is_(None),
                )
            )
            .order_by(VerificationDocument.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_documents_for_context(
        self, context_id: UUID
    ) -> List[VerificationDocument]:
        """Return the document linked to a context (0 or 1 items)."""
        ctx = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.id == str(context_id))
            .first()
        )
        if ctx is None or ctx.document_id is None:
            return []
        doc = self.get_document_by_id(ctx.document_id)
        return [doc] if doc else []

    # ------------------------------------------------------------------
    # Context-document link (one document per context via FK)
    # ------------------------------------------------------------------

    def link_document_to_context(
        self, context_id: UUID, document_id: UUID
    ) -> None:
        """Set a context's linked document (replaces any existing link)."""
        ctx = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.id == str(context_id))
            .first()
        )
        if ctx is None:
            return
        ctx.document_id = str(document_id)
        self.db.commit()

    def unlink_document_from_context(
        self, context_id: UUID, document_id: UUID
    ) -> bool:
        """Clear the context's document FK if it matches. Returns False otherwise."""
        ctx = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.id == str(context_id))
            .first()
        )
        if ctx is None or str(ctx.document_id) != str(document_id):
            return False
        ctx.document_id = None
        self.db.commit()
        return True

    def is_document_linked_to_context(
        self, context_id: UUID, document_id: UUID
    ) -> bool:
        """Check whether the context references this document."""
        ctx = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.id == str(context_id))
            .first()
        )
        return ctx is not None and str(ctx.document_id) == str(document_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_document_status(
        self,
        document_id: UUID,
        status: VerificationStatus,
        reviewer_id: UUID,
        reviewer_notes: Optional[str] = None,
        document_expiry_date: Optional[date] = None,
        rejection_reason: Optional[str] = None,
    ) -> Optional[VerificationDocument]:
        """
        Transition a document to a new verification status.

        Sets review metadata (reviewer, timestamp, notes) alongside
        the status change.
        """
        doc = self.get_document_by_id(document_id)
        if doc is None:
            return None

        doc.verification_status = status
        doc.reviewer_id = str(reviewer_id)
        doc.reviewed_at = datetime.now(timezone.utc)
        doc.reviewer_notes = reviewer_notes
        doc.document_expiry_date = document_expiry_date
        doc.rejection_reason = rejection_reason
        doc.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(doc)
        return doc

    # ------------------------------------------------------------------
    # Delete (soft)
    # ------------------------------------------------------------------

    def soft_delete_document(self, document_id: UUID) -> bool:
        """Mark a document as deleted. Returns False if not found."""
        doc = self.get_document_by_id(document_id)
        if doc is None:
            return False

        doc.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return True
