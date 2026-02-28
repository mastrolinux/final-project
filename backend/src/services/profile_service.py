"""
Profile Service

Business logic layer for profile management.
Implements validation rules and account type constraints.
"""

import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from src.models.audit import AuditEventType, AuditOperation
from src.models.profile import AccountType, BaseProfile, IdentityName
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.profile import IdentityNameCreate, IdentityNameUpdate, ProfileCreate, ProfileUpdate

if TYPE_CHECKING:
    from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ProfileServiceError(Exception):
    """Custom exception for profile service errors"""

    pass


class ProfileService:
    """Service layer for profile business logic"""

    def __init__(
        self,
        repository: ProfileRepository,
        audit_service: Optional["AuditService"] = None,
        auth_repository: AuthRepository | None = None,
    ):
        self.repository = repository
        self.audit_service = audit_service
        self.auth_repo = auth_repository

    def create_profile(self, profile_data: ProfileCreate) -> BaseProfile:
        """Create a new profile with business logic validation."""
        if profile_data.account_type == AccountType.verified and not profile_data.legal_name:
            raise ProfileServiceError("Verified accounts require a legal_name")

        existing = self.repository.get_profile_by_email(profile_data.primary_email)
        if existing:
            raise ProfileServiceError(
                f"Profile with email {profile_data.primary_email} already exists"
            )

        profile = self.repository.create_profile(
            account_type=profile_data.account_type,
            legal_name=profile_data.legal_name,
            primary_email=profile_data.primary_email,
            primary_phone=profile_data.primary_phone,
            preferred_language=profile_data.preferred_language,
        )

        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.profile_create,
                user_id=profile.user_id,
                actor_id=profile.user_id,
                resource_type="profile",
                resource_id=str(profile.user_id),
                operation=AuditOperation.create,
                changes={
                    "account_type": profile_data.account_type.value,
                    "primary_email": profile_data.primary_email,
                },
                legal_basis="contract",
            )

        return profile

    def get_profile(self, user_id: UUID) -> BaseProfile:
        """Get profile by ID or raise ProfileServiceError."""
        profile = self.repository.get_profile_by_id(user_id)

        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")

        return profile

    def get_profile_with_names(
        self, user_id: UUID, include_deprecated: bool = False
    ) -> tuple[BaseProfile, list[IdentityName]]:
        """Get profile with its identity names."""
        profile, names = self.repository.get_profile_with_names(
            user_id, include_deprecated=include_deprecated
        )

        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")

        return profile, names

    def update_profile(self, user_id: UUID, update_data: ProfileUpdate) -> BaseProfile:
        """Update profile with account-type transition and email-uniqueness validation."""
        existing = self.repository.get_profile_by_id(user_id)
        if not existing:
            raise ProfileServiceError(f"Profile {user_id} not found")

        if update_data.account_type is not None:
            if update_data.account_type == AccountType.verified:
                legal_name = update_data.legal_name or existing.legal_name
                if not legal_name:
                    raise ProfileServiceError(
                        "Cannot upgrade to verified account without legal_name"
                    )

            if existing.account_type == AccountType.verified:
                if update_data.account_type != AccountType.verified:
                    raise ProfileServiceError("Cannot downgrade from verified account type")

        email_changed = False
        if update_data.primary_email:
            if update_data.primary_email != existing.primary_email:
                duplicate = self.repository.get_profile_by_email(update_data.primary_email)
                if duplicate:
                    raise ProfileServiceError(f"Email {update_data.primary_email} already in use")
                email_changed = True

        updates = {}
        for field in [
            "account_type",
            "legal_name",
            "primary_email",
            "primary_phone",
            "preferred_language",
        ]:
            value = getattr(update_data, field)
            if value is not None:
                updates[field] = value

        profile = self.repository.update_profile(user_id, **updates)

        if email_changed and self.auth_repo:
            token = self.auth_repo.update_email(str(user_id), update_data.primary_email)
            if token:
                display_name = existing.legal_name or "User"
                try:
                    from src.tasks.email_tasks import send_verification_email

                    send_verification_email.delay(update_data.primary_email, token, display_name)
                except Exception:
                    logger.warning("Failed to dispatch verification email for %s", user_id)
            profile.email_verification_pending = True  # type: ignore[attr-defined]

        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.profile_update,
                user_id=user_id,
                actor_id=user_id,
                resource_type="profile",
                resource_id=str(user_id),
                operation=AuditOperation.update,
                changes={"fields_updated": list(updates.keys())},
                legal_basis="contract",
            )

        return profile

    def delete_profile(self, user_id: UUID) -> bool:
        """Soft delete a profile."""
        result = self.repository.soft_delete_profile(user_id)

        if not result:
            raise ProfileServiceError(f"Profile {user_id} not found")

        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.profile_delete,
                user_id=user_id,
                actor_id=user_id,
                resource_type="profile",
                resource_id=str(user_id),
                operation=AuditOperation.delete,
                legal_basis="contract",
            )

        return result

    def add_identity_name(self, user_id: UUID, name_data: IdentityNameCreate) -> IdentityName:
        """Add an identity name to a profile."""
        profile = self.repository.get_profile_by_id(user_id)
        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")

        name = self.repository.create_identity_name(
            identity_id=user_id,
            name_type=name_data.name_type,
            name_value=name_data.name_value,
            is_primary=name_data.is_primary,
            is_deprecated=name_data.is_deprecated,
            visibility_level=name_data.visibility_level,
            context_id=name_data.context_id,
        )

        return name

    def update_identity_name(
        self, user_id: UUID, name_id: UUID, update_data: IdentityNameUpdate
    ) -> IdentityName:
        """Update an identity name after verifying ownership."""
        name = self.repository.get_identity_name_by_id(name_id)
        if not name:
            raise ProfileServiceError(f"Identity name {name_id} not found")
        if name.identity_id != user_id:
            raise ProfileServiceError(f"Identity name {name_id} does not belong to user {user_id}")

        updates = {
            k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None
        }
        if not updates:
            return name

        updated = self.repository.update_identity_name(name_id, **updates)
        return updated

    def delete_identity_name(self, user_id: UUID, name_id: UUID) -> bool:
        """Delete an identity name after verifying ownership."""
        name = self.repository.get_identity_name_by_id(name_id)
        if not name:
            raise ProfileServiceError(f"Identity name {name_id} not found")
        if name.identity_id != user_id:
            raise ProfileServiceError(f"Identity name {name_id} does not belong to user {user_id}")

        return self.repository.delete_identity_name(name_id)
