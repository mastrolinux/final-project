"""
Audit Log Schemas

Pydantic models for audit log API responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogEntry(BaseModel):
    """Single audit log entry response."""

    log_id: UUID
    created_at: datetime
    event_type: str
    user_id: UUID | None = None
    actor_id: UUID | None = None
    resource_type: str
    resource_id: str
    operation: str
    changes: dict[str, Any] | None = None
    ip_address: str | None = None
    legal_basis: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditTrailResponse(BaseModel):
    """Paginated audit trail response."""

    entries: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class AuditIntegrityResponse(BaseModel):
    """Hash chain integrity verification response."""

    is_valid: bool
    entries_verified: int
    error_message: str | None = None
