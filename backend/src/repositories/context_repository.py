"""
Context Repository

Data access layer for ContextProfile entities.
Handles all database operations for context profile management.
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from src.models.context import ContextProfile, ContextType
from src.models.verification import VerificationStatus


class ContextRepository:
    """Repository for ContextProfile database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_context_profile(
        self,
        user_id: UUID,
        context_type: ContextType,
        context_name: str,
        display_name_override: str | None = None,
        email_override: str | None = None,
        phone_override: str | None = None,
        bio: str | None = None,
        is_active: bool = True,
        verification_status: Optional["VerificationStatus"] = None,
    ) -> ContextProfile:
        """Create a new context profile."""
        context = ContextProfile(
            user_id=user_id,
            context_type=context_type,
            context_name=context_name,
            display_name_override=display_name_override,
            email_override=email_override,
            phone_override=phone_override,
            bio=bio,
            is_active=is_active,
            verification_status=verification_status,
        )

        self.db.add(context)
        self.db.commit()
        self.db.refresh(context)

        return context

    def get_context_profile_by_id(self, context_id: UUID) -> ContextProfile | None:
        """Get context profile by ID, excluding soft-deleted."""
        return (
            self.db.query(ContextProfile)
            .filter(and_(ContextProfile.id == context_id, ContextProfile.deleted_at.is_(None)))
            .first()
        )

    def get_user_context_profiles(
        self, user_id: UUID, include_inactive: bool = False
    ) -> list[ContextProfile]:
        """Get all context profiles for a user, excluding soft-deleted."""
        query = (
            self.db.query(ContextProfile)
            .options(joinedload(ContextProfile.document))
            .filter(and_(ContextProfile.user_id == user_id, ContextProfile.deleted_at.is_(None)))
        )

        if not include_inactive:
            query = query.filter(ContextProfile.is_active == True)

        return query.order_by(ContextProfile.created_at.asc()).all()

    def get_context_by_type_and_name(
        self, user_id: UUID, context_type: ContextType, context_name: str
    ) -> ContextProfile | None:
        """Get context profile by user, type, and name."""
        return (
            self.db.query(ContextProfile)
            .filter(
                and_(
                    ContextProfile.user_id == user_id,
                    ContextProfile.context_type == context_type,
                    ContextProfile.context_name == context_name,
                    ContextProfile.deleted_at.is_(None),
                )
            )
            .first()
        )

    def update_context_profile(self, context_id: UUID, **updates) -> ContextProfile | None:
        """Update context profile fields."""
        context = self.get_context_profile_by_id(context_id)

        if not context:
            return None

        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)

        context.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(context)

        return context

    def soft_delete_context_profile(self, context_id: UUID) -> bool:
        """Soft delete a context profile by setting deleted_at timestamp."""
        context = self.db.query(ContextProfile).filter(ContextProfile.id == context_id).first()

        if not context or context.deleted_at is not None:
            return False

        context.deleted_at = datetime.now(UTC)

        self.db.commit()

        return True

    def count_user_contexts(self, user_id: UUID, active_only: bool = True) -> int:
        """Count number of context profiles for a user."""
        query = self.db.query(ContextProfile).filter(
            and_(ContextProfile.user_id == user_id, ContextProfile.deleted_at.is_(None))
        )

        if active_only:
            query = query.filter(ContextProfile.is_active == True)

        return query.count()

    def soft_delete_user_contexts(self, user_id: UUID) -> int:
        """Soft delete all context profiles for a user."""
        now = datetime.now(UTC)
        count = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.user_id == user_id, ContextProfile.deleted_at.is_(None))
            .update({ContextProfile.deleted_at: now}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def update_verification_status(
        self,
        context_id: UUID,
        verification_status: VerificationStatus,
        is_active: bool,
        rejection_reason: str | None = None,
    ) -> ContextProfile | None:
        """Update verification status and active flag for admin approve/reject."""
        context = self.db.query(ContextProfile).filter(ContextProfile.id == context_id).first()

        if not context:
            return None

        context.verification_status = verification_status
        context.is_active = is_active
        context.rejection_reason = rejection_reason
        context.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(context)

        return context

    def get_contexts_pending_verification(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContextProfile]:
        """Return contexts awaiting verification that have a linked document.

        Eagerly loads base_profile for display_name access.
        """
        return (
            self.db.query(ContextProfile)
            .options(joinedload(ContextProfile.base_profile))
            .filter(
                and_(
                    ContextProfile.verification_status.in_(
                        [
                            VerificationStatus.pending,
                            VerificationStatus.under_review,
                        ]
                    ),
                    ContextProfile.deleted_at.is_(None),
                    ContextProfile.document_id.isnot(None),
                )
            )
            .order_by(ContextProfile.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_active_contexts_by_document_id(self, document_id: UUID) -> list[ContextProfile]:
        """Return active, non-deleted contexts linked to the given document.

        Used by the expiry task to deactivate contexts when their
        backing verification document expires.
        """
        return (
            self.db.query(ContextProfile)
            .filter(
                and_(
                    ContextProfile.document_id == str(document_id),
                    ContextProfile.is_active == True,
                    ContextProfile.deleted_at.is_(None),
                )
            )
            .all()
        )

    def restore_user_contexts(self, user_id: UUID) -> int:
        """Restore all soft-deleted context profiles for a user."""
        count = (
            self.db.query(ContextProfile)
            .filter(ContextProfile.user_id == user_id, ContextProfile.deleted_at.isnot(None))
            .update({ContextProfile.deleted_at: None}, synchronize_session=False)
        )
        self.db.commit()
        return count
