"""
Profile Schemas

Pydantic models for profile request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models.profile import AccountType, NameType, VisibilityLevel


class ProfileCreate(BaseModel):
    """Schema for creating a new profile"""

    account_type: AccountType = Field(
        default=AccountType.unverified,
        description="Account type: verified, unverified, or pseudonymous",
    )
    legal_name: str | None = Field(
        default=None, max_length=255, description="Legal name (required for verified accounts)"
    )
    primary_email: EmailStr = Field(
        ..., description="Primary email address (required, must be unique)"
    )
    primary_phone: str | None = Field(
        default=None, max_length=50, description="Primary phone number"
    )
    preferred_language: str = Field(
        default="en", max_length=10, description="Preferred language code (ISO 639-1)"
    )

    @field_validator("primary_email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email"""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("legal_name", "primary_phone", mode="before")
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
                    "account_type": "verified",
                    "legal_name": "Sarah Elizabeth Chen",
                    "primary_email": "sarah.chen@example.com",
                    "primary_phone": "+1-555-0101",
                    "preferred_language": "en",
                }
            ]
        }
    )


class ProfileUpdate(BaseModel):
    """Schema for updating an existing profile"""

    account_type: AccountType | None = None
    legal_name: str | None = Field(default=None, max_length=255)
    primary_email: EmailStr | None = None
    primary_phone: str | None = Field(default=None, max_length=50)
    preferred_language: str | None = Field(default=None, max_length=10)

    @field_validator("primary_email", mode="before")
    @classmethod
    def strip_email(cls, v):
        """Strip whitespace from email"""
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("legal_name", "primary_phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None"""
        if v == "":
            return None
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"primary_phone": "+1-555-9999", "preferred_language": "es"}]
        }
    )


class ProfileResponse(BaseModel):
    """Schema for profile response"""

    user_id: UUID
    account_type: AccountType
    legal_name: str | None = None
    primary_email: str
    primary_phone: str | None = None
    preferred_language: str
    avatar_url: str | None = None
    avatar_thumbnail_url: str | None = None
    email_verification_pending: bool = Field(
        default=False, description="True when the email was just changed and needs re-verification"
    )
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
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "account_type": "verified",
                    "legal_name": "Sarah Elizabeth Chen",
                    "primary_email": "sarah.chen@example.com",
                    "primary_phone": "+1-555-0101",
                    "preferred_language": "en",
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "valid_from": "2025-01-01T00:00:00Z",
                    "valid_to": None,
                }
            ]
        },
    )


class IdentityNameCreate(BaseModel):
    """Schema for creating a new identity name"""

    name_type: NameType = Field(
        ..., description="Type of name: given, family, preferred, legal, etc."
    )
    name_value: dict[str, str] = Field(
        ..., description="Multilingual name values (language code: name)"
    )
    is_primary: bool = Field(
        default=False, description="Whether this is the primary name of this type"
    )
    is_deprecated: bool = Field(
        default=False, description="Whether this name is deprecated (e.g., deadname)"
    )
    visibility_level: VisibilityLevel = Field(
        default=VisibilityLevel.public,
        description="Visibility level: public, private, or historical_suppressed",
    )
    context_id: UUID | None = Field(
        default=None, description="Optional context ID if this name is context-specific"
    )

    @field_validator("name_value")
    @classmethod
    def validate_name_value_not_empty(cls, v):
        """Validate that name_value dict is not empty"""
        if not v:
            raise ValueError("name_value must contain at least one language-name pair")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name_type": "full_name",
                    "name_value": {"en": "Dr. Sarah Chen", "zh": "陈莎拉博士"},
                    "is_primary": True,
                    "visibility_level": "public",
                }
            ]
        }
    )


class IdentityNameUpdate(BaseModel):
    """Schema for updating an existing identity name"""

    name_value: dict[str, str] | None = None
    is_primary: bool | None = None
    is_deprecated: bool | None = None
    visibility_level: VisibilityLevel | None = None

    @field_validator("name_value")
    @classmethod
    def validate_name_value_not_empty(cls, v):
        """Validate that name_value dict is not empty if provided"""
        if v is not None and not v:
            raise ValueError("name_value must contain at least one language-name pair")
        return v

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"is_primary": True, "visibility_level": "private"}]}
    )


class IdentityNameResponse(BaseModel):
    """Schema for identity name response"""

    id: UUID
    identity_id: UUID
    name_type: NameType
    name_value: dict[str, str]
    is_primary: bool
    is_deprecated: bool
    visibility_level: VisibilityLevel
    context_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    valid_from: datetime
    valid_to: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174001",
                    "identity_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name_type": "full_name",
                    "name_value": {"en": "Dr. Sarah Chen"},
                    "is_primary": True,
                    "is_deprecated": False,
                    "visibility_level": "public",
                    "context_id": None,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                    "valid_from": "2025-01-01T00:00:00Z",
                    "valid_to": None,
                }
            ]
        },
    )
