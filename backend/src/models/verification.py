"""
Verification Document Model

SQLAlchemy model for identity verification documents.
Tracks uploaded government-issued ID documents through a
verification workflow: pending -> under_review -> verified/rejected.
"""

import enum
import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.profile import UUID, SoftDeleteMixin, TimestampMixin


class DocumentType(str, enum.Enum):
    """Supported government-issued ID document types."""

    passport = "passport"
    national_id = "national_id"


class VerificationStatus(str, enum.Enum):
    """Verification workflow states."""

    pending = "pending"
    under_review = "under_review"
    verified = "verified"
    rejected = "rejected"
    expired = "expired"


class VerificationDocument(Base, TimestampMixin, SoftDeleteMixin):
    """Identity verification document, encrypted at rest via Fernet."""

    __tablename__ = "verification_documents"

    id = Column(
        UUID(),
        primary_key=True,
        default=lambda: str(uuid_pkg.uuid4()),
    )

    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type = Column(
        SQLEnum(DocumentType, name="document_type", create_type=False),
        nullable=False,
    )

    verification_status = Column(
        SQLEnum(VerificationStatus, name="verification_status", create_type=False),
        nullable=False,
        default=VerificationStatus.pending,
    )

    storage_path = Column(Text, nullable=True)
    original_filename = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    content_type = Column(String(50), nullable=False)

    reviewer_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    document_expiry_date = Column(Date, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    user = relationship(
        "BaseProfile",
        foreign_keys=[user_id],
        backref="verification_documents",
    )

    @property
    def is_verified(self) -> bool:
        """Return True if this document has been verified by an admin."""
        return self.verification_status == VerificationStatus.verified

    @property
    def is_reviewable(self) -> bool:
        """Return True if this document can still be reviewed."""
        return self.verification_status in (
            VerificationStatus.pending,
            VerificationStatus.under_review,
        )

    @property
    def is_expired(self) -> bool:
        """Return True if the physical document has passed its expiry date (UTC)."""
        if self.document_expiry_date is None:
            return False
        return self.document_expiry_date < datetime.now(UTC).date()

    def __repr__(self) -> str:
        return (
            f"<VerificationDocument(id={self.id}, user={self.user_id}, "
            f"type={self.document_type}, status={self.verification_status})>"
        )
