"""
Avatar Service

Business logic for uploading and deleting profile avatars.
"""

import logging
import uuid as uuid_pkg
from typing import Optional
from uuid import UUID

from src.core.image import ImageProcessingError, process_avatar_image
from src.core.storage import StorageClient
from src.models.audit import AuditEventType, AuditOperation
from src.repositories.avatar_repository import AvatarRepository
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AvatarServiceError(Exception):
    """Domain exception for avatar operations."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AvatarService:
    """Orchestrates avatar upload and deletion for base and context profiles."""

    def __init__(
        self,
        avatar_repo: AvatarRepository,
        storage: StorageClient,
        audit_service: Optional[AuditService] = None,
    ):
        self.avatar_repo = avatar_repo
        self.storage = storage
        self.audit_service = audit_service


# Base profile avatar
    def upload_base_avatar(
        self, user_id: UUID, file_data: bytes
    ) -> dict:
        """Upload or replace the base profile avatar."""
        profile = self.avatar_repo.get_base_profile(user_id)
        if not profile:
            raise AvatarServiceError(
                f"Profile {user_id} not found", status_code=404
            )

        try:
            processed = process_avatar_image(file_data)
        except ImageProcessingError as exc:
            raise AvatarServiceError(str(exc)) from exc

        if profile.avatar_storage_path:
            self._delete_storage_pair(profile.avatar_storage_path)

        prefix = f"{user_id}/{uuid_pkg.uuid4().hex}"
        avatar_result = self.storage.upload(
            f"{prefix}/avatar.webp", processed.avatar, processed.content_type
        )
        thumbnail_result = self.storage.upload(
            f"{prefix}/thumbnail.webp", processed.thumbnail, processed.content_type
        )

        self.avatar_repo.update_base_avatar(
            user_id=user_id,
            avatar_url=avatar_result.public_url,
            avatar_thumbnail_url=thumbnail_result.public_url,
            avatar_storage_path=prefix,
        )

        self._audit(
            AuditEventType.avatar_upload,
            user_id=user_id,
            resource_type="base_profile",
            resource_id=str(user_id),
        )

        return {
            "avatar_url": avatar_result.public_url,
            "avatar_thumbnail_url": thumbnail_result.public_url,
            "message": "Avatar uploaded successfully",
        }

    def delete_base_avatar(self, user_id: UUID) -> dict:
        """Remove the base profile avatar."""
        profile = self.avatar_repo.get_base_profile(user_id)
        if not profile:
            raise AvatarServiceError(
                f"Profile {user_id} not found", status_code=404
            )

        if not profile.avatar_storage_path:
            raise AvatarServiceError("Profile does not have an avatar")

        self._delete_storage_pair(profile.avatar_storage_path)

        self.avatar_repo.update_base_avatar(
            user_id=user_id,
            avatar_url=None,
            avatar_thumbnail_url=None,
            avatar_storage_path=None,
        )

        self._audit(
            AuditEventType.avatar_delete,
            user_id=user_id,
            resource_type="base_profile",
            resource_id=str(user_id),
        )

        return {"message": "Avatar deleted successfully"}

# Context profile avatar override
    def upload_context_avatar(
        self, user_id: UUID, context_id: UUID, file_data: bytes
    ) -> dict:
        """Upload or replace a context-specific avatar override."""
        context = self._get_verified_context(user_id, context_id)

        try:
            processed = process_avatar_image(file_data)
        except ImageProcessingError as exc:
            raise AvatarServiceError(str(exc)) from exc

        if context.avatar_override_storage_path:
            self._delete_storage_pair(context.avatar_override_storage_path)

        prefix = f"{user_id}/contexts/{context_id}/{uuid_pkg.uuid4().hex}"
        avatar_result = self.storage.upload(
            f"{prefix}/avatar.webp", processed.avatar, processed.content_type
        )
        thumbnail_result = self.storage.upload(
            f"{prefix}/thumbnail.webp", processed.thumbnail, processed.content_type
        )

        self.avatar_repo.update_context_avatar(
            context_id=context_id,
            avatar_override_url=avatar_result.public_url,
            avatar_override_thumbnail_url=thumbnail_result.public_url,
            avatar_override_storage_path=prefix,
        )

        self._audit(
            AuditEventType.avatar_upload,
            user_id=user_id,
            resource_type="context_profile",
            resource_id=str(context_id),
        )

        return {
            "avatar_url": avatar_result.public_url,
            "avatar_thumbnail_url": thumbnail_result.public_url,
            "message": "Context avatar uploaded successfully",
        }

    def delete_context_avatar(self, user_id: UUID, context_id: UUID) -> dict:
        """Remove the context-specific avatar override; context inherits base avatar."""
        context = self._get_verified_context(user_id, context_id)

        if not context.avatar_override_storage_path:
            raise AvatarServiceError(
                "Context profile does not have an avatar override"
            )

        self._delete_storage_pair(context.avatar_override_storage_path)

        self.avatar_repo.update_context_avatar(
            context_id=context_id,
            avatar_override_url=None,
            avatar_override_thumbnail_url=None,
            avatar_override_storage_path=None,
        )

        self._audit(
            AuditEventType.avatar_delete,
            user_id=user_id,
            resource_type="context_profile",
            resource_id=str(context_id),
        )

        return {"message": "Context avatar deleted successfully"}


# Helpers
    def _get_verified_context(self, user_id: UUID, context_id: UUID):
        """Load a context profile and verify it belongs to the given user."""
        context = self.avatar_repo.get_context_profile(context_id)
        if not context:
            raise AvatarServiceError(
                f"Context profile {context_id} not found", status_code=404
            )
        if context.user_id != user_id:
            raise AvatarServiceError(
                f"Context {context_id} does not belong to user {user_id}",
                status_code=403,
            )
        return context

    def _delete_storage_pair(self, prefix: str) -> None:
        """Delete both avatar and thumbnail objects under a storage prefix."""
        self.storage.delete(f"{prefix}/avatar.webp")
        self.storage.delete(f"{prefix}/thumbnail.webp")

    def _audit(
        self,
        event_type: AuditEventType,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Record an audit event if the audit service is available."""
        if not self.audit_service:
            return
        self.audit_service.log_event(
            event_type=event_type,
            user_id=user_id,
            actor_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            operation=AuditOperation.update,
        )
