"""
Privacy Schemas

Pydantic models for GDPR Article 15 data export API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProfileExport(BaseModel):
    """Base profile data for export."""
    user_id: UUID
    account_type: str
    legal_name: Optional[str] = None
    primary_email: str
    primary_phone: Optional[str] = None
    preferred_language: str
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IdentityNameExport(BaseModel):
    """Identity name data for export."""
    id: UUID
    name_type: str
    name_value: Dict[str, Any]
    is_primary: bool
    is_deprecated: bool
    visibility_level: str
    context_id: Optional[UUID] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ContextProfileExport(BaseModel):
    """Context profile data for export."""
    id: UUID
    context_type: str
    context_name: str
    display_name_override: Optional[str] = None
    email_override: Optional[str] = None
    phone_override: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuthenticationExport(BaseModel):
    """Authentication metadata for export (excludes sensitive fields)."""
    email: str
    is_email_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    is_admin: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OAuthConsentExport(BaseModel):
    """OAuth consent record for export."""
    id: UUID
    client_id: str
    granted_scopes: List[str]
    context_profile_id: Optional[UUID] = None
    consent_method: str
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GDPRMetadata(BaseModel):
    """Static GDPR Article 15 metadata accompanying the export."""
    processing_purposes: List[str]
    retention_periods: Dict[str, str]
    data_subject_rights: List[str]
    data_sources: List[str]
    recipients_or_categories: List[str]
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
    identity_names: List[IdentityNameExport]
    context_profiles: List[ContextProfileExport]
    authentication: AuthenticationExport
    oauth_consents: List[OAuthConsentExport]
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
    deletion_scheduled_at: Optional[str] = None
    permanent_deletion_date: Optional[str] = None
