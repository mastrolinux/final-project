"""
Context Service

Business logic layer for context profile management.
Implements the inheritance engine for profile resolution.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.core.types import UNSET, _Unset
from src.models.audit import AuditEventType, AuditOperation
from src.models.context import ContextProfile, ContextType
from src.models.profile import AccountType, IdentityName
from src.models.verification import VerificationStatus
from src.repositories.auth_repository import AuthRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository

if TYPE_CHECKING:
    from src.services.audit_service import AuditService


class ContextServiceError(Exception):
    """Custom exception for context service errors"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ResolvedProfile:
    """Unified view combining base profile + context overrides."""

    def __init__(
        self,
        user_id: UUID,
        account_type: AccountType,
        display_name: str | None,
        email: str,
        phone: str | None,
        preferred_language: str,
        bio: str | None,
        context_type: ContextType | None = None,
        context_name: str | None = None,
        identity_names: list[IdentityName] | None = None,
        avatar_url: str | None = None,
        avatar_thumbnail_url: str | None = None,
    ):
        self.user_id = user_id
        self.account_type = account_type
        self.display_name = display_name
        self.email = email
        self.phone = phone
        self.preferred_language = preferred_language
        self.bio = bio
        self.context_type = context_type
        self.context_name = context_name
        self.identity_names = identity_names or []
        self.avatar_url = avatar_url
        self.avatar_thumbnail_url = avatar_thumbnail_url

    def to_dict(self) -> dict[str, Any]:
        """Convert resolved profile to dictionary for API responses"""
        return {
            "user_id": str(self.user_id),
            "account_type": self.account_type.value,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "preferred_language": self.preferred_language,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "avatar_thumbnail_url": self.avatar_thumbnail_url,
            "context_type": self.context_type.value if self.context_type else None,
            "context_name": self.context_name,
            "identity_names": [
                {
                    "name_type": name.name_type.value,
                    "name_value": name.name_value,
                    "is_primary": name.is_primary,
                }
                for name in self.identity_names
            ],
        }


class ContextService:
    """Service layer for context profile business logic"""

    def __init__(
        self,
        context_repository: ContextRepository,
        profile_repository: ProfileRepository,
        audit_service: Optional["AuditService"] = None,
        auth_repository: AuthRepository | None = None,
    ):
        self.context_repo = context_repository
        self.profile_repo = profile_repository
        self.audit_service = audit_service
        self.auth_repo = auth_repository

    def _resolve_multilingual_name(
        self, name: IdentityName, requested_language: str, preferred_language: str
    ) -> str:
        """Resolve name value using BCP 47 fallback.

        Order: requested -> preferred -> 'en' -> first available.
        """
        name_value = name.name_value  # JSONB dict: {"en": "Sarah", "zh": "萨拉"}

        if not isinstance(name_value, dict):
            return ""

        # Try requested language (highest priority)
        if requested_language in name_value:
            return name_value[requested_language]

        # Try user's preferred language
        if preferred_language in name_value:
            return name_value[preferred_language]

        # Try English default (universal fallback)
        if "en" in name_value:
            return name_value["en"]

        # Use first available language alphabetically
        if name_value:
            first_key = sorted(name_value.keys())[0]
            return name_value[first_key]

        return ""

    def create_context_profile(
        self,
        user_id: UUID,
        context_type: ContextType,
        context_name: str,
        display_name_override: str | None = None,
        email_override: str | None = None,
        phone_override: str | None = None,
        bio: str | None = None,
    ) -> ContextProfile:
        """Create a new context profile with business logic validation."""
        # Verify base profile exists
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")

        # Business rule: email must be verified before creating any context
        if self.auth_repo is not None:
            auth_user = self.auth_repo.get_by_user_id(str(user_id))
            if auth_user and not auth_user.is_email_verified:
                raise ContextServiceError(
                    "Email verification required before creating context profiles", status_code=403
                )

        # Business rule: pseudonymous accounts cannot create legal/healthcare contexts
        if context_type in [ContextType.legal, ContextType.healthcare]:
            if base_profile.account_type == AccountType.pseudonymous:
                raise ContextServiceError(
                    f"Pseudonymous accounts cannot create {context_type.value} contexts.",
                    status_code=403,
                )

        # Check for duplicate context (user_id, context_type, context_name)
        existing = self.context_repo.get_context_by_type_and_name(
            user_id, context_type, context_name
        )
        if existing:
            raise ContextServiceError(
                f"Context '{context_name}' of type"
                f" {context_type.value} already exists for this user"
            )

        # Validate email override format if provided
        if email_override:
            # Basic email validation (in production, use email validator library)
            if "@" not in email_override or "." not in email_override:
                raise ContextServiceError("Invalid email override format")

        # Legal/healthcare contexts start inactive and require verification
        requires_verification = context_type in [ContextType.legal, ContextType.healthcare]
        initial_active = not requires_verification
        initial_verification_status = VerificationStatus.pending if requires_verification else None

        # Create context profile
        try:
            context = self.context_repo.create_context_profile(
                user_id=user_id,
                context_type=context_type,
                context_name=context_name,
                display_name_override=display_name_override,
                email_override=email_override,
                phone_override=phone_override,
                bio=bio,
                is_active=initial_active,
                verification_status=initial_verification_status,
            )
        except IntegrityError:
            raise ContextServiceError(
                f"Context '{context_name}' of type {context_type.value} "
                f"already exists for this user",
                status_code=409,
            )

        # Audit: context creation
        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.context_create,
                user_id=user_id,
                actor_id=user_id,
                resource_type="context",
                resource_id=str(context.id),
                operation=AuditOperation.create,
                changes={
                    "context_type": context_type.value,
                    "context_name": context_name,
                },
                legal_basis="contract",
            )

        return context

    def _enrich_expiry_status(self, context: ContextProfile) -> ContextProfile:
        """Project verification_status as 'expired' when the linked document's
        expiry date has passed. Celery Beat handles the canonical state
        transition. Uses set_committed_value to modify the in-memory
        attribute without marking the object as dirty."""
        if (
            context.verification_status == VerificationStatus.verified
            and context.document is not None
            and context.document.is_expired
        ):
            from sqlalchemy.orm.attributes import set_committed_value

            set_committed_value(context, "verification_status", VerificationStatus.expired)
            set_committed_value(context, "is_active", False)
        return context

    def get_context_profile(self, context_id: UUID) -> ContextProfile:
        """Get context profile by ID. Raises ContextServiceError if not found."""
        context = self.context_repo.get_context_profile_by_id(context_id)

        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")

        return self._enrich_expiry_status(context)

    def get_user_contexts(
        self, user_id: UUID, include_inactive: bool = False
    ) -> list[ContextProfile]:
        """Get all context profiles for a user."""
        contexts = self.context_repo.get_user_context_profiles(
            user_id, include_inactive=include_inactive
        )
        return [self._enrich_expiry_status(ctx) for ctx in contexts]

    def update_context_profile(
        self,
        context_id: UUID,
        display_name_override: str | None | _Unset = UNSET,
        email_override: str | None | _Unset = UNSET,
        phone_override: str | None | _Unset = UNSET,
        bio: str | None | _Unset = UNSET,
        is_active: bool | None | _Unset = UNSET,
        context_name: str | None | _Unset = UNSET,
    ) -> ContextProfile:
        """Update context profile. UNSET keeps existing, None clears override."""
        # Get existing context
        context = self.context_repo.get_context_profile_by_id(context_id)
        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")

        # Validate email override format if provided and not null
        if email_override is not UNSET and email_override is not None:
            if "@" not in email_override or "." not in email_override:
                raise ContextServiceError("Invalid email override format")

        # Build update dict - include field if it was explicitly provided (even if None)
        updates = {}
        if display_name_override is not UNSET:
            updates["display_name_override"] = display_name_override
        if email_override is not UNSET:
            updates["email_override"] = email_override
        if phone_override is not UNSET:
            updates["phone_override"] = phone_override
        if bio is not UNSET:
            updates["bio"] = bio
        if is_active is not UNSET and is_active is not None:
            # is_active should not be cleared to None (always bool)
            updates["is_active"] = is_active
        if context_name is not UNSET and context_name is not None:
            # context_name should not be cleared to None (always required)
            updates["context_name"] = context_name

        # Re-verification: if identity fields change on a verified
        # legal/healthcare context, reset verification to pending
        identity_fields = {"display_name_override", "email_override"}
        identity_changed = any(k in identity_fields for k in updates)
        if (
            identity_changed
            and context.requires_verification
            and context.verification_status == VerificationStatus.verified
        ):
            updates["verification_status"] = VerificationStatus.pending
            updates["is_active"] = False

        # Update context
        updated_context = self.context_repo.update_context_profile(context_id, **updates)

        # Audit: context update
        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.context_update,
                user_id=context.user_id,
                actor_id=context.user_id,
                resource_type="context",
                resource_id=str(context_id),
                operation=AuditOperation.update,
                changes={"fields_updated": list(updates.keys())},
                legal_basis="contract",
            )

        return updated_context

    def delete_context_profile(self, context_id: UUID) -> bool:
        """Soft delete a context profile."""
        # Get context before deletion for audit user_id
        context = self.context_repo.get_context_profile_by_id(context_id)

        result = self.context_repo.soft_delete_context_profile(context_id)

        if not result:
            raise ContextServiceError(f"Context profile {context_id} not found")

        # Audit: context deletion (soft delete)
        if self.audit_service and context:
            self.audit_service.log_event(
                event_type=AuditEventType.context_delete,
                user_id=context.user_id,
                actor_id=context.user_id,
                resource_type="context",
                resource_id=str(context_id),
                operation=AuditOperation.delete,
                legal_basis="contract",
            )

        return result

    def resolve_context_profile(
        self,
        user_id: UUID,
        context_id: UUID,
        language: str = "en",
        include_deprecated_names: bool = False,
    ) -> ResolvedProfile:
        """Merge base profile + context overrides into a ResolvedProfile."""
        # Get base profile
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")

        # Get context profile
        context = self.context_repo.get_context_profile_by_id(context_id)
        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")

        # Verify context belongs to user
        if context.user_id != user_id:
            raise ContextServiceError(f"Context {context_id} does not belong to user {user_id}")

        # Check temporal validity (HTTP 410 Gone for expired contexts)
        now = datetime.now(UTC)
        if context.valid_to and context.valid_to < now:
            raise ContextServiceError(
                f"Context profile expired on {context.valid_to.isoformat()}. "
                f"This context is no longer valid.",
                status_code=410,
            )

        # Get identity names
        _, identity_names = self.profile_repo.get_profile_with_names(
            user_id, include_deprecated=include_deprecated_names
        )

        # INHERITANCE ENGINE: Merge base + overrides
        # Start with base profile values
        resolved_display_name = None
        resolved_email = base_profile.primary_email
        resolved_phone = base_profile.primary_phone
        resolved_bio = None
        # Avatars are NOT inherited from the base profile.  Each context
        # must have an explicit avatar_override or it returns None (privacy-
        # by-design: the user's base photo is never leaked into a context
        # without explicit consent).
        resolved_avatar_url = None
        resolved_avatar_thumbnail_url = None

        # Apply context overrides (null means inherit from base)
        if context.display_name_override is not None:
            resolved_display_name = context.display_name_override

        if context.email_override is not None:
            resolved_email = context.email_override

        if context.phone_override is not None:
            resolved_phone = context.phone_override

        if context.bio is not None:
            resolved_bio = context.bio

        if context.avatar_override_url is not None:
            resolved_avatar_url = context.avatar_override_url
            resolved_avatar_thumbnail_url = context.avatar_override_thumbnail_url

        # Resolve multilingual names with fallback chain
        # Apply language-specific name resolution for each identity name
        resolved_names = []
        for name in identity_names:
            # Resolve multilingual value (used for future per-language response)
            self._resolve_multilingual_name(
                name,
                requested_language=language,
                preferred_language=base_profile.preferred_language,
            )
            # Keep the IdentityName object but note the resolved language
            # (For now, we keep the full JSONB for backward compatibility)
            # In a future enhancement, we could return only the resolved string
            resolved_names.append(name)

        # Create resolved profile
        resolved = ResolvedProfile(
            user_id=user_id,
            account_type=base_profile.account_type,
            display_name=resolved_display_name,
            email=resolved_email,
            phone=resolved_phone,
            preferred_language=base_profile.preferred_language,
            bio=resolved_bio,
            context_type=context.context_type,
            context_name=context.context_name,
            identity_names=resolved_names,
            avatar_url=resolved_avatar_url,
            avatar_thumbnail_url=resolved_avatar_thumbnail_url,
        )

        return resolved

    def resolve_base_profile(
        self, user_id: UUID, language: str = "en", include_deprecated_names: bool = False
    ) -> ResolvedProfile:
        """Resolve base profile without context overrides."""
        # Get base profile
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")

        # Get identity names
        _, identity_names = self.profile_repo.get_profile_with_names(
            user_id, include_deprecated=include_deprecated_names
        )

        # Create resolved profile without context
        resolved = ResolvedProfile(
            user_id=user_id,
            account_type=base_profile.account_type,
            display_name=None,  # No override
            email=base_profile.primary_email,
            phone=base_profile.primary_phone,
            preferred_language=base_profile.preferred_language,
            bio=None,  # No context-specific bio
            context_type=None,
            context_name=None,
            identity_names=identity_names,
            avatar_url=base_profile.avatar_url,
            avatar_thumbnail_url=base_profile.avatar_thumbnail_url,
        )

        return resolved
