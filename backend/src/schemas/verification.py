"""
Verification Document Schemas

Pydantic models for request validation and response serialization
of identity verification documents and admin review operations.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.models.profile import AccountType
from src.models.verification import DocumentType, VerificationStatus


class VerificationDocumentResponse(BaseModel):
    """Public representation of a verification document (omits storage_path)."""

    id: UUID
    user_id: UUID
    document_type: DocumentType
    verification_status: VerificationStatus
    original_filename: str
    file_size_bytes: int
    content_type: str
    document_expiry_date: date | None = None
    rejection_reason: str | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "user_id": "11111111-1111-1111-1111-111111111111",
                    "document_type": "passport",
                    "verification_status": "pending",
                    "original_filename": "passport_scan.pdf",
                    "file_size_bytes": 2048576,
                    "content_type": "application/pdf",
                    "document_expiry_date": "2030-06-15",
                    "rejection_reason": None,
                    "reviewer_notes": None,
                    "reviewed_at": None,
                    "created_at": "2026-02-20T10:00:00Z",
                    "updated_at": "2026-02-20T10:00:00Z",
                }
            ]
        },
    )


class VerificationStatusResponse(BaseModel):
    """Summary of a user's verification state."""

    user_id: UUID
    account_type: AccountType
    latest_document: VerificationDocumentResponse | None = None
    can_create_legal_context: bool

    model_config = ConfigDict(from_attributes=True)


class AdminVerificationReview(BaseModel):
    """Admin request body for approving or rejecting a verification document."""

    verification_status: VerificationStatus = Field(
        ...,
        description="Target status: must be 'verified' or 'rejected'",
    )
    reviewer_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Internal notes visible to admins only",
    )
    document_expiry_date: date | None = Field(
        default=None,
        description="Physical document expiry date; null means no expiry",
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Reason for rejection (required when rejecting)",
    )

    @field_validator("verification_status")
    @classmethod
    def must_be_terminal_status(cls, v: VerificationStatus) -> VerificationStatus:
        """Only verified and rejected are valid review outcomes."""
        if v not in (VerificationStatus.verified, VerificationStatus.rejected):
            raise ValueError("Review status must be 'verified' or 'rejected'")
        return v

    @model_validator(mode="after")
    def rejection_reason_required_when_rejected(self) -> "AdminVerificationReview":
        """Ensure a rejection reason is provided when rejecting."""
        if self.verification_status == VerificationStatus.rejected and not self.rejection_reason:
            raise ValueError("rejection_reason is required when status is 'rejected'")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "verification_status": "verified",
                    "reviewer_notes": "Passport matches profile name",
                    "document_expiry_date": "2030-06-15",
                },
                {
                    "verification_status": "rejected",
                    "rejection_reason": "Document image is not legible",
                },
            ]
        },
    )


class AdminContextVerificationItem(BaseModel):
    """Context entry for the admin pending-verification list."""

    context_id: UUID
    context_type: str
    context_name: str
    display_name_override: str | None = None
    email_override: str | None = None
    verification_status: str
    user_id: UUID
    user_display_name: str | None = None
    document_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminContextVerificationDetail(BaseModel):
    """Full context details with linked documents for admin review."""

    context_id: UUID
    context_type: str
    context_name: str
    display_name_override: str | None = None
    email_override: str | None = None
    phone_override: str | None = None
    bio: str | None = None
    verification_status: str
    rejection_reason: str | None = None
    user_id: UUID
    user_display_name: str | None = None
    documents: list[VerificationDocumentResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
