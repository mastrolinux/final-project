"""
Admin User Management Schemas

Pydantic models for admin user management endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SoftDeletedUserResponse(BaseModel):
    """Response schema for a soft-deleted user."""

    user_id: str
    email: str
    is_email_verified: bool
    is_admin: bool
    deleted_at: datetime
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SoftDeletedUserListResponse(BaseModel):
    """Paginated list of soft-deleted users."""

    users: List[SoftDeletedUserResponse]
    total: int
    page: int = 1
    page_size: int = 20


class PurgeExpiredResponse(BaseModel):
    """Response from purging expired soft-deleted accounts."""

    purged_count: int
