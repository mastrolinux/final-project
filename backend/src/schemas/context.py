"""
Context Profile Schemas

Pydantic models for context profile request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models.context import ContextType
from src.models.profile import AccountType, NameType


class ContextProfileCreate(BaseModel):
    """Schema for creating a new context profile"""

    context_type: ContextType = Field(
        ..., description="Type of context: professional, social, legal, or healthcare"
    )
    context_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User-defined context name (e.g., 'Work', 'LinkedIn', 'Family')",
    )
    display_name_override: str | None = Field(
        default=None, max_length=255, description="Override display name for this context"
    )
    email_override: EmailStr | None = Field(
        default=None, description="Override email for this context"
    )
    phone_override: str | None = Field(
        default=None, max_length=50, description="Override phone number for this context"
    )
    bio: str | None = Field(
        default=None, max_length=1000, description="Context-specific biography or description"
    )

    @field_validator("context_name", mode="before")
    @classmethod
    def strip_context_name(cls, v):
        """Strip whitespace from context name"""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "display_name_override", "email_override", "phone_override", "bio", mode="before"
    )
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None"""
        if v == "":
            return None
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "context_type": "professional",
                    "context_name": "LinkedIn",
                    "display_name_override": "Dr. Sarah Chen, MD, PhD",
                    "email_override": "s.chen@hospital.org",
                    "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
                }
            ]
        }
    )


class ContextProfileUpdate(BaseModel):
    """Schema for updating an existing context profile"""

    context_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name_override: str | None = Field(default=None, max_length=255)
    email_override: EmailStr | None = None
    phone_override: str | None = Field(default=None, max_length=50)
    bio: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None

    @field_validator("context_name", mode="before")
    @classmethod
    def strip_context_name(cls, v):
        """Strip whitespace from context name"""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator(
        "display_name_override", "email_override", "phone_override", "bio", mode="before"
    )
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None"""
        if v == "":
            return None
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"bio": "Updated professional biography", "is_active": True}]
        }
    )


class ContextProfileResponse(BaseModel):
    """Schema for context profile response (raw context with overrides only)"""

    id: UUID
    user_id: UUID
    context_type: ContextType
    context_name: str
    display_name_override: str | None = None
    email_override: str | None = None
    phone_override: str | None = None
    bio: str | None = None
    avatar_override_url: str | None = None
    avatar_override_thumbnail_url: str | None = None
    is_active: bool
    verification_status: str | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    valid_from: datetime
    valid_to: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "123e4567-e89b-12d3-a456-426614174001",
                    "context_type": "professional",
                    "context_name": "LinkedIn",
                    "display_name_override": "Dr. Sarah Chen, MD, PhD",
                    "email_override": "s.chen@hospital.org",
                    "phone_override": None,
                    "bio": "Board-certified psychiatrist",
                    "is_active": True,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "deleted_at": None,
                    "valid_from": "2025-01-01T00:00:00Z",
                    "valid_to": None,
                }
            ]
        },
    )


class IdentityNameInResolved(BaseModel):
    """Schema for identity name in resolved profile"""

    name_type: NameType
    name_value: dict[str, str]
    is_primary: bool

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name_type": "full_name",
                    "name_value": {"en": "Dr. Sarah Chen", "zh": "陈莎拉博士"},
                    "is_primary": True,
                }
            ]
        }
    )


class ResolvedProfileResponse(BaseModel):
    """Schema for fully resolved profile (base + context overrides applied)."""

    user_id: UUID
    account_type: AccountType
    display_name: str | None = Field(
        None, description="Display name (from context override or None if not overridden)"
    )
    email: str = Field(..., description="Email address (from context override or base profile)")
    phone: str | None = Field(
        None, description="Phone number (from context override or base profile)"
    )
    preferred_language: str
    bio: str | None = Field(None, description="Biography (context-specific if available)")
    avatar_url: str | None = Field(
        None,
        description=("Avatar URL (from context override only; not inherited from base profile)"),
    )
    avatar_thumbnail_url: str | None = Field(
        None,
        description=(
            "Avatar thumbnail URL (from context override only; not inherited from base profile)"
        ),
    )
    context_type: ContextType | None = Field(
        None, description="Context type this profile is resolved for"
    )
    context_name: str | None = Field(None, description="Context name this profile is resolved for")
    identity_names: list[IdentityNameInResolved] = Field(
        default_factory=list, description="Identity names (filtered for deprecated if applicable)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "123e4567-e89b-12d3-a456-426614174001",
                    "account_type": "verified",
                    "display_name": "Dr. Sarah Chen, MD, PhD",
                    "email": "s.chen@hospital.org",
                    "phone": "+1-555-0101",
                    "preferred_language": "en",
                    "bio": "Board-certified psychiatrist specializing in trauma and PTSD",
                    "context_type": "professional",
                    "context_name": "LinkedIn",
                    "identity_names": [
                        {
                            "name_type": "full_name",
                            "name_value": {"en": "Dr. Sarah Chen"},
                            "is_primary": True,
                        }
                    ],
                }
            ]
        }
    )
