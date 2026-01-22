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
from src.models.oauth import OAuthClient
from src.repositories.oauth_repository import OAuthRepository
from src.schemas.oauth import (
    OAuthClientCreate,
    OAuthClientUpdate,
    OAuthClientResponse,
    OAuthClientCreateResponse,
    OAuthClientListResponse
)


router = APIRouter()


def get_oauth_repository(db: Session = Depends(get_db)) -> OAuthRepository:
    """Dependency to get OAuthRepository instance"""
    return OAuthRepository(db)


# =============================================================================
# OAuth Client CRUD Endpoints
# =============================================================================

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
    oauth_repo: OAuthRepository = Depends(get_oauth_repository)
):
    """
    Create a new OAuth client.
    
    For confidential clients, a client_secret is required and will be hashed.
    The plain text secret is returned ONLY in this response - store it securely.
    
    For public clients (is_confidential=False), no secret is needed.
    """
    # Check if client_id already exists
    existing = oauth_repo.get_client(client_data.client_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Client with ID '{client_data.client_id}' already exists"
        )
    
    # Handle client secret for confidential clients
    plain_secret = None
    secret_hash = None
    
    if client_data.is_confidential:
        if client_data.client_secret:
            # Use provided secret
            plain_secret = client_data.client_secret
        else:
            # Generate a secure random secret
            plain_secret = secrets.token_urlsafe(32)
        
        # Hash the secret using Argon2id (same as passwords)
        secret_hash = hash_password(plain_secret)
    
    # Create the client model
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
    
    # Save to database
    created_client = oauth_repo.create_client(client)
    
    # Return response with plain secret (only time it's shown)
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
        client_secret=plain_secret  # Only returned on creation
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
    """
    List all OAuth clients with pagination.
    
    By default, only active clients are returned.
    Use include_inactive=true to see all clients including deactivated ones.
    """
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
    """
    Get details of a specific OAuth client.
    
    Note: The client_secret is never returned - it can only be seen
    at creation time or by generating a new one via PATCH.
    """
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
    oauth_repo: OAuthRepository = Depends(get_oauth_repository)
):
    """
    Update an OAuth client.
    
    Only provided fields are updated. To update the client_secret,
    include it in the request body (it will be hashed).
    """
    client = oauth_repo.get_client(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    # Update fields if provided
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Handle client_secret separately (needs hashing)
    if "client_secret" in update_dict:
        new_secret = update_dict.pop("client_secret")
        if new_secret:
            client.client_secret_hash = hash_password(new_secret)
    
    # Update other fields
    for field, value in update_dict.items():
        if hasattr(client, field):
            setattr(client, field, value)
    
    # Save changes
    updated_client = oauth_repo.update_client(client)
    
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
    oauth_repo: OAuthRepository = Depends(get_oauth_repository)
):
    """
    Soft-delete an OAuth client.
    
    The client is marked as inactive (is_active=false) and its deleted_at
    timestamp is set. The client record is preserved for audit purposes.
    
    All existing tokens for this client will continue to work until they
    expire, but no new tokens can be issued.
    """
    client = oauth_repo.get_client(client_id)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found"
        )
    
    # Soft delete (sets deleted_at and is_active=false)
    oauth_repo.delete_client(client_id)
    
    return None
