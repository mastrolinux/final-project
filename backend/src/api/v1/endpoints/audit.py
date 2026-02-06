"""
Audit Log API Endpoints

Provides data subject access to their audit trail
and admin access for integrity verification.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.api.dependencies.auth import get_current_user, require_admin
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.services.audit_service import AuditService
from src.schemas.audit import (
    AuditTrailResponse,
    AuditLogEntry,
    AuditIntegrityResponse
)

router = APIRouter()


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Dependency to get AuditService instance."""
    audit_repo = AuditRepository(db)
    return AuditService(audit_repo)


@router.get(
    "/me",
    response_model=AuditTrailResponse,
    summary="Get My Audit Trail",
    description="Retrieve your audit trail (data subject access)"
)
def get_my_audit_trail(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200, description="Max entries per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: AuthUser = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service)
):
    """Get audit trail for the authenticated user."""
    result = service.get_user_audit_trail(
        user_id=current_user.user_id,
        event_type=event_type,
        resource_type=resource_type,
        limit=limit,
        offset=offset
    )
    return AuditTrailResponse(
        entries=[AuditLogEntry.model_validate(e) for e in result["entries"]],
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"]
    )


@router.get(
    "/verify",
    response_model=AuditIntegrityResponse,
    summary="Verify Audit Log Integrity",
    description="Verify hash chain integrity (admin only)"
)
def verify_audit_integrity(
    limit: int = Query(1000, ge=1, le=10000, description="Entries to verify"),
    current_user: AuthUser = Depends(require_admin),
    service: AuditService = Depends(get_audit_service)
):
    """Verify hash chain integrity of audit logs."""
    is_valid, verified, error = service.verify_integrity(limit=limit)
    return AuditIntegrityResponse(
        is_valid=is_valid,
        entries_verified=verified,
        error_message=error
    )
