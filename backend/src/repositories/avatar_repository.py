"""
Avatar Repository

Data access layer for avatar-related columns on BaseProfile and ContextProfile.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.context import ContextProfile
from src.models.profile import BaseProfile


class AvatarRepository:
    """Repository for reading and writing avatar fields on profile models."""

    def __init__(self, db: Session):
        self.db = db

    #
    # Base profile avatar operations
    #

    def get_base_profile(self, user_id: UUID) -> BaseProfile | None:
        """Retrieve a base profile by user_id, ignoring soft-deleted records."""
        return (
            self.db.query(BaseProfile)
            .filter(
                BaseProfile.user_id == user_id,
                BaseProfile.deleted_at.is_(None),
            )
            .first()
        )

    def update_base_avatar(
        self,
        user_id: UUID,
        avatar_url: str | None,
        avatar_thumbnail_url: str | None,
        avatar_storage_path: str | None,
    ) -> BaseProfile | None:
        """
        Set or clear avatar fields on a base profile.

        Pass None for all three parameters to clear the avatar.
        """
        profile = self.get_base_profile(user_id)
        if not profile:
            return None

        profile.avatar_url = avatar_url
        profile.avatar_thumbnail_url = avatar_thumbnail_url
        profile.avatar_storage_path = avatar_storage_path
        profile.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    #
    # Context profile avatar operations
    #

    def get_context_profile(self, context_id: UUID) -> ContextProfile | None:
        """Retrieve a context profile by id, ignoring soft-deleted records."""
        return (
            self.db.query(ContextProfile)
            .filter(
                ContextProfile.id == context_id,
                ContextProfile.deleted_at.is_(None),
            )
            .first()
        )

    def update_context_avatar(
        self,
        context_id: UUID,
        avatar_override_url: str | None,
        avatar_override_thumbnail_url: str | None,
        avatar_override_storage_path: str | None,
    ) -> ContextProfile | None:
        """
        Set or clear avatar override fields on a context profile.

        Pass None for all three parameters to clear the override
        (the context will then inherit the base profile avatar).
        """
        context = self.get_context_profile(context_id)
        if not context:
            return None

        context.avatar_override_url = avatar_override_url
        context.avatar_override_thumbnail_url = avatar_override_thumbnail_url
        context.avatar_override_storage_path = avatar_override_storage_path
        context.updated_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(context)
        return context
