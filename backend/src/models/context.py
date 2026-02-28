"""
Context Profile Models

SQLAlchemy models for context-dependent identity profiles.
Implements multi-context identity presentation based on Goffman's dramaturgical theory.
"""

import enum
import uuid as uuid_pkg
from typing import Any

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.profile import UUID, SoftDeleteMixin, TemporalMixin, TimestampMixin
from src.models.verification import VerificationStatus


class ContextType(str, enum.Enum):
    """Context type enumeration for different social contexts"""

    professional = "professional"
    social = "social"
    legal = "legal"
    healthcare = "healthcare"
    family = "family"
    custom = "custom"


class ContextProfile(Base, TimestampMixin, SoftDeleteMixin, TemporalMixin):
    """Context-dependent identity overrides; null fields inherit from base profile."""

    __tablename__ = "context_profiles"

    id = Column(UUID(), primary_key=True, default=uuid_pkg.uuid4)

    user_id = Column(
        UUID(), ForeignKey("base_profiles.user_id", ondelete="CASCADE"), nullable=False
    )

    context_type = Column(SQLEnum(ContextType, name="context_type"), nullable=False)

    context_name = Column(Text, nullable=False)

    display_name_override = Column(Text, nullable=True)
    email_override = Column(String(255), nullable=True)
    phone_override = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)

    avatar_override_url = Column(Text, nullable=True)
    avatar_override_thumbnail_url = Column(Text, nullable=True)
    avatar_override_storage_path = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    verification_status = Column(
        SQLEnum(VerificationStatus, name="verification_status", create_type=False),
        nullable=True,
    )
    rejection_reason = Column(Text, nullable=True)

    base_profile = relationship("BaseProfile", foreign_keys=[user_id], backref="context_profiles")
    document_id = Column(
        UUID(),
        ForeignKey("verification_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document = relationship(
        "VerificationDocument",
        foreign_keys=[document_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ContextProfile(id={self.id}, user_id={self.user_id},"
            f" type={self.context_type}, name={self.context_name})>"
        )

    @property
    def requires_verification(self) -> bool:
        """Return True if this context type requires identity verification."""
        return self.context_type in (ContextType.legal, ContextType.healthcare)

    @property
    def is_identity_verified(self) -> bool:
        """Return True if this context has been identity-verified by an admin."""
        return self.verification_status == VerificationStatus.verified

    def has_overrides(self) -> bool:
        """Check if this context has any field overrides"""
        return any(
            [
                self.display_name_override is not None,
                self.email_override is not None,
                self.phone_override is not None,
                self.bio is not None,
                self.avatar_override_url is not None,
            ]
        )

    def get_override_fields(self) -> dict[str, Any]:
        """Get non-null override fields as a dict."""
        overrides = {}

        if self.display_name_override is not None:
            overrides["display_name"] = self.display_name_override
        if self.email_override is not None:
            overrides["email"] = self.email_override
        if self.phone_override is not None:
            overrides["phone"] = self.phone_override
        if self.bio is not None:
            overrides["bio"] = self.bio
        if self.avatar_override_url is not None:
            overrides["avatar_url"] = self.avatar_override_url
            overrides["avatar_thumbnail_url"] = self.avatar_override_thumbnail_url

        return overrides
