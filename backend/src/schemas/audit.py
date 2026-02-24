"""
Audit Log Schemas

Pydantic models for audit log API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogEntry(BaseModel):
    """Single audit log entry response."""
    log_id: UUID
    created_at: datetime
    event_type: str
    user_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    resource_type: str
    resource_id: str
    operation: str
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    legal_basis: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditTrailResponse(BaseModel):
    """Paginated audit trail response."""
    entries: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


class AuditIntegrityResponse(BaseModel):
    """Hash chain integrity verification response."""
    is_valid: bool
    entries_verified: int
    error_message: Optional[str] = None
