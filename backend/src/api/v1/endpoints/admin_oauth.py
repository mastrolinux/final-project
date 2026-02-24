"""
Admin OAuth Client Management Endpoints

REST API endpoints for managing OAuth clients.
All endpoints require admin privileges.
"""

from typing import Optional
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import hash_password
from src.api.dependencies.auth import require_admin
from src.models.auth import AuthUser
from src.models.audit import AuditEventType, AuditOperation
from src.models.oauth import OAuthClient
from src.repositories.oauth_repository import OAuthRepository
from src.repositories.audit_repository import AuditRepository
from src.services.audit_service import AuditService
from src.schemas.oauth import (
    OAuthClientCreate,
    OAuthClientUpdate,
    OAuthClientResponse,
    OAuthClientCreateResponse,
    OAuthClientListResponse
)


router = APIRouter()


def get_oauth_repository(db: Session = Depends(get_db)) -> OAuthRepository:
    """Dependency to get OAuthRepository instance."""
    return OAuthRepository(db)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Dependency to get AuditService instance for admin audit logging."""
    return AuditService(AuditRepository(db))


#
# OAuth Client CRUD Endpoints
#

@router.post(
    "/clients",
    response_model=OAuthClientCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OAuth Client",
    description="Register a new OAuth client. Requires admin privileges."
)
def create_oauth_client(
    client_data: OAuthClientCreate,
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Create a new OAuth client. Plain text secret is only returned in this response."""
    if oauth_repo.client_id_exists(client_data.client_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Client with ID '{client_data.client_id}' already exists or was previously deleted"
        )
    
    plain_secret = None
    secret_hash = None
    
    if client_data.is_confidential:
        if client_data.client_secret:
            plain_secret = client_data.client_secret
        else:
            plain_secret = secrets.token_urlsafe(32)
        secret_hash = hash_password(plain_secret)

    client = OAuthClient(
        client_id=client_data.client_id,
        client_secret_hash=secret_hash,
        client_name=client_data.client_name,
        client_description=client_data.client_description,
        client_uri=client_data.client_uri,
        logo_uri=client_data.logo_uri,
        redirect_uris=client_data.redirect_uris,
        allowed_scopes=client_data.allowed_scopes,
        default_context_type=client_data.default_context_type,
        is_confidential=client_data.is_confidential,
        is_first_party=client_data.is_first_party,
        is_active=True
    )
    
    created_client = oauth_repo.create_client(client)

    audit_service.log_event(
        event_type=AuditEventType.client_create,
        user_id=admin.user_id,
        actor_id=admin.user_id,
        resource_type="oauth_client",
        resource_id=created_client.client_id,
        operation=AuditOperation.create,
        changes={"client_name": created_client.client_name},
        legal_basis="legitimate_interest"
    )

    return OAuthClientCreateResponse(
        client_id=created_client.client_id,
        client_name=created_client.client_name,
        client_description=created_client.client_description,
        client_uri=created_client.client_uri,
        logo_uri=created_client.logo_uri,
        redirect_uris=created_client.redirect_uris,
        allowed_scopes=created_client.allowed_scopes,
        default_context_type=created_client.default_context_type,
        is_confidential=created_client.is_confidential,
        is_active=created_client.is_active,
        is_first_party=created_client.is_first_party,
        created_at=created_client.created_at,
        client_secret=plain_secret
    )


@router.get(
    "/clients",
    response_model=OAuthClientListResponse,
    summary="List OAuth Clients",
    description="List all registered OAuth clients. Requires admin privileges."
)
def list_oauth_clients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive clients"),
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository)
):
    """List all OAuth clients with pagination."""
    clients = oauth_repo.list_all_clients(
        include_inactive=include_inactive,
        offset=(page - 1) * page_size,
        limit=page_size
    )
    
    total = oauth_repo.count_clients(include_inactive=include_inactive)
    
    return OAuthClientListResponse(
        clients=[
            OAuthClientResponse(
                client_id=c.client_id,
                client_name=c.client_name,
                client_description=c.client_description,
                client_uri=c.client_uri,
                logo_uri=c.logo_uri,
                redirect_uris=c.redirect_uris,
                allowed_scopes=c.allowed_scopes,
                default_context_type=c.default_context_type,
                is_confidential=c.is_confidential,
                is_active=c.is_active,
                is_first_party=c.is_first_party,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in clients
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/clients/{client_id}",
    response_model=OAuthClientResponse,
    summary="Get OAuth Client",
    description="Get details of a specific OAuth client. Requires admin privileges."
)
def get_oauth_client(
    client_id: str,
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository)
):
    """Get details of a specific OAuth client. Secret is never returned."""
    client = oauth_repo.get_client(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    return OAuthClientResponse(
        client_id=client.client_id,
        client_name=client.client_name,
        client_description=client.client_description,
        client_uri=client.client_uri,
        logo_uri=client.logo_uri,
        redirect_uris=client.redirect_uris,
        allowed_scopes=client.allowed_scopes,
        default_context_type=client.default_context_type,
        is_confidential=client.is_confidential,
        is_active=client.is_active,
        is_first_party=client.is_first_party,
        created_at=client.created_at,
        updated_at=client.updated_at
    )


@router.patch(
    "/clients/{client_id}",
    response_model=OAuthClientResponse,
    summary="Update OAuth Client",
    description="Update an OAuth client. Requires admin privileges."
)
def update_oauth_client(
    client_id: str,
    update_data: OAuthClientUpdate,
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Update an OAuth client. Only provided fields are changed."""
    client = oauth_repo.get_client(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)

    if "client_secret" in update_dict:
        new_secret = update_dict.pop("client_secret")
        if new_secret:
            client.client_secret_hash = hash_password(new_secret)
    
    for field, value in update_dict.items():
        if hasattr(client, field):
            setattr(client, field, value)
    
    updated_client = oauth_repo.update_client(client)

    audit_service.log_event(
        event_type=AuditEventType.client_update,
        user_id=admin.user_id,
        actor_id=admin.user_id,
        resource_type="oauth_client",
        resource_id=client_id,
        operation=AuditOperation.update,
        changes=update_data.model_dump(exclude_unset=True, exclude={"client_secret"}),
        legal_basis="legitimate_interest"
    )

    return OAuthClientResponse(
        client_id=updated_client.client_id,
        client_name=updated_client.client_name,
        client_description=updated_client.client_description,
        client_uri=updated_client.client_uri,
        logo_uri=updated_client.logo_uri,
        redirect_uris=updated_client.redirect_uris,
        allowed_scopes=updated_client.allowed_scopes,
        default_context_type=updated_client.default_context_type,
        is_confidential=updated_client.is_confidential,
        is_active=updated_client.is_active,
        is_first_party=updated_client.is_first_party,
        created_at=updated_client.created_at,
        updated_at=updated_client.updated_at
    )


@router.delete(
    "/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete OAuth Client",
    description="Soft-delete an OAuth client. Requires admin privileges."
)
def delete_oauth_client(
    client_id: str,
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Soft-delete an OAuth client. Existing tokens remain valid until expiry."""
    client = oauth_repo.get_client(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    oauth_repo.delete_client(client_id)

    audit_service.log_event(
        event_type=AuditEventType.client_delete,
        user_id=admin.user_id,
        actor_id=admin.user_id,
        resource_type="oauth_client",
        resource_id=client_id,
        operation=AuditOperation.delete,
        legal_basis="legitimate_interest"
    )

    return None


@router.delete(
    "/clients/{client_id}/purge",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently Delete OAuth Client",
    description="Hard-delete an OAuth client and all related records. Requires admin privileges."
)
def purge_oauth_client(
    client_id: str,
    admin: AuthUser = Depends(require_admin),
    oauth_repo: OAuthRepository = Depends(get_oauth_repository),
    audit_service: AuditService = Depends(get_audit_service)
):
    """Hard-delete an OAuth client and all related records. Irreversible."""
    if not oauth_repo.client_id_exists(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    # Record audit event before purge since the data will be gone after
    audit_service.log_event(
        event_type=AuditEventType.client_purge,
        user_id=admin.user_id,
        actor_id=admin.user_id,
        resource_type="oauth_client",
        resource_id=client_id,
        operation=AuditOperation.delete,
        changes={"hard_delete": True},
        legal_basis="legitimate_interest"
    )

    oauth_repo.purge_client(client_id)

    return None
