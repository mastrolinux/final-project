"""
Privacy Schemas

Pydantic models for GDPR Article 15 data export API responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileExport(BaseModel):
    """Base profile data for export."""

    user_id: UUID
    account_type: str
    legal_name: str | None = None
    primary_email: str
    primary_phone: str | None = None
    preferred_language: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class IdentityNameExport(BaseModel):
    """Identity name data for export."""

    id: UUID
    name_type: str
    name_value: dict[str, Any]
    is_primary: bool
    is_deprecated: bool
    visibility_level: str
    context_id: UUID | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ContextProfileExport(BaseModel):
    """Context profile data for export."""

    id: UUID
    context_type: str
    context_name: str
    display_name_override: str | None = None
    email_override: str | None = None
    phone_override: str | None = None
    bio: str | None = None
    is_active: bool
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthenticationExport(BaseModel):
    """Authentication metadata for export (excludes sensitive fields)."""

    email: str
    is_email_verified: bool
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    is_admin: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OAuthConsentExport(BaseModel):
    """OAuth consent record for export."""

    id: UUID
    client_id: str
    granted_scopes: list[str]
    context_profile_id: UUID | None = None
    consent_method: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    withdrawn_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GDPRMetadata(BaseModel):
    """Static GDPR Article 15 metadata accompanying the export."""

    processing_purposes: list[str]
    retention_periods: dict[str, str]
    data_subject_rights: list[str]
    data_sources: list[str]
    recipients_or_categories: list[str]
    automated_decision_making: str


class ExportMetadata(BaseModel):
    """Export envelope metadata."""

    exported_at: datetime
    user_id: UUID
    format_version: str
    legal_basis: str


class DataExportResponse(BaseModel):
    """Complete GDPR Article 15 data export response."""

    export_metadata: ExportMetadata
    profile: ProfileExport
    identity_names: list[IdentityNameExport]
    context_profiles: list[ContextProfileExport]
    authentication: AuthenticationExport
    oauth_consents: list[OAuthConsentExport]
    gdpr_metadata: GDPRMetadata


class DeletionRequestResponse(BaseModel):
    """Response for account deletion request."""

    status: str
    deletion_scheduled_at: str
    permanent_deletion_date: str
    message: str


class DeletionStatusResponse(BaseModel):
    """Response for deletion status check."""

    status: str
    deletion_scheduled_at: str | None = None
    permanent_deletion_date: str | None = None
