"""
Context Profile API Endpoints

REST API endpoints for context profile management.
Implements multi-context identity presentation based on Goffman's dramaturgical theory.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.types import UNSET
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.auth_repository import AuthRepository
from src.repositories.audit_repository import AuditRepository
from src.services.context_service import ContextService, ContextServiceError
from src.services.audit_service import AuditService
from src.api.dependencies.auth import require_verified_user
from src.models.auth import AuthUser
from src.schemas.context import (
    ContextProfileCreate,
    ContextProfileUpdate,
    ContextProfileResponse,
    ResolvedProfileResponse
)


router = APIRouter()


def get_context_service(db: Session = Depends(get_db)) -> ContextService:
    """Dependency to get ContextService instance with audit logging."""
    context_repo = ContextRepository(db)
    profile_repo = ProfileRepository(db)
    auth_repo = AuthRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return ContextService(
        context_repo, profile_repo,
        audit_service=audit_service,
        auth_repository=auth_repo
    )


def parse_accept_language(
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
) -> str:
    """Extract primary language code from Accept-Language header (RFC 7231)."""
    if not accept_language:
        return "en"

    languages = accept_language.split(',')

    if languages:
        primary = languages[0].strip()
        lang_code = primary.split('-')[0].split(';')[0].strip()
        
        return lang_code if lang_code else "en"
    
    return "en"


@router.post(
    "/profiles/{user_id}/contexts",
    response_model=ContextProfileResponse,
    status_code=status.HTTP_201_CREATED
)
def create_context_profile(
    user_id: UUID,
    context_data: ContextProfileCreate,
    service: ContextService = Depends(get_context_service),
    _current_user: AuthUser = Depends(require_verified_user)
):
    """Create a new context profile for a user."""
    try:
        context = service.create_context_profile(
            user_id=user_id,
            context_type=context_data.context_type,
            context_name=context_data.context_name,
            display_name_override=context_data.display_name_override,
            email_override=context_data.email_override,
            phone_override=context_data.phone_override,
            bio=context_data.bio
        )
        return context
    except ContextServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        elif e.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/profiles/{user_id}/contexts",
    response_model=List[ContextProfileResponse]
)
def list_user_contexts(
    user_id: UUID,
    include_inactive: bool = Query(
        default=False,
        description="Include inactive contexts in results"
    ),
    service: ContextService = Depends(get_context_service)
):
    """List all context profiles for a user (raw overrides only)."""
    contexts = service.get_user_contexts(user_id, include_inactive=include_inactive)
    return contexts


@router.get(
    "/profiles/{user_id}/contexts/{context_id}",
    response_model=ContextProfileResponse
)
def get_context_profile(
    user_id: UUID,
    context_id: UUID,
    service: ContextService = Depends(get_context_service)
):
    """Get a specific context profile (raw overrides only)."""
    try:
        context = service.get_context_profile(context_id)
        
        if context.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Context {context_id} does not belong to user {user_id}"
            )
        
        return context
    except ContextServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/profiles/{user_id}/contexts/{context_id}/resolved",
    response_model=ResolvedProfileResponse
)
def get_resolved_context_profile(
    user_id: UUID,
    context_id: UUID,
    include_deprecated: bool = Query(
        default=False,
        description="Include deprecated names in results"
    ),
    language: str = Depends(parse_accept_language),
    service: ContextService = Depends(get_context_service)
):
    """Get fully resolved profile with context inheritance applied."""
    try:
        resolved = service.resolve_context_profile(
            user_id=user_id,
            context_id=context_id,
            language=language,
            include_deprecated_names=include_deprecated
        )

        return ResolvedProfileResponse(
            user_id=resolved.user_id,
            account_type=resolved.account_type,
            display_name=resolved.display_name,
            email=resolved.email,
            phone=resolved.phone,
            preferred_language=resolved.preferred_language,
            bio=resolved.bio,
            avatar_url=resolved.avatar_url,
            avatar_thumbnail_url=resolved.avatar_thumbnail_url,
            context_type=resolved.context_type,
            context_name=resolved.context_name,
            identity_names=[
                {
                    "name_type": name.name_type,
                    "name_value": name.name_value,
                    "is_primary": name.is_primary
                }
                for name in resolved.identity_names
            ]
        )
    except ContextServiceError as e:
        status_code = getattr(e, 'status_code', None)

        if status_code:
            raise HTTPException(
                status_code=status_code,
                detail=str(e)
            )
        elif "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "does not belong" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/profiles/{user_id}/resolved",
    response_model=ResolvedProfileResponse
)
def get_resolved_base_profile(
    user_id: UUID,
    include_deprecated: bool = Query(
        default=False,
        description="Include deprecated names in results"
    ),
    language: str = Depends(parse_accept_language),
    service: ContextService = Depends(get_context_service)
):
    """Get resolved base profile without context overrides."""
    try:
        resolved = service.resolve_base_profile(
            user_id=user_id,
            language=language,
            include_deprecated_names=include_deprecated
        )
        
        return ResolvedProfileResponse(
            user_id=resolved.user_id,
            account_type=resolved.account_type,
            display_name=resolved.display_name,
            email=resolved.email,
            phone=resolved.phone,
            preferred_language=resolved.preferred_language,
            bio=resolved.bio,
            avatar_url=resolved.avatar_url,
            avatar_thumbnail_url=resolved.avatar_thumbnail_url,
            context_type=resolved.context_type,
            context_name=resolved.context_name,
            identity_names=[
                {
                    "name_type": name.name_type,
                    "name_value": name.name_value,
                    "is_primary": name.is_primary
                }
                for name in resolved.identity_names
            ]
        )
    except ContextServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch(
    "/profiles/{user_id}/contexts/{context_id}",
    response_model=ContextProfileResponse
)
def update_context_profile(
    user_id: UUID,
    context_id: UUID,
    update_data: ContextProfileUpdate,
    service: ContextService = Depends(get_context_service),
    _current_user: AuthUser = Depends(require_verified_user)
):
    """Update a context profile. Null clears an override; omitted fields are unchanged."""
    try:
        context = service.get_context_profile(context_id)
        if context.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Context {context_id} does not belong to user {user_id}"
            )

        provided_fields = update_data.model_fields_set

        updated = service.update_context_profile(
            context_id=context_id,
            context_name=(
                update_data.context_name if 'context_name' in provided_fields else UNSET
            ),
            display_name_override=(
                update_data.display_name_override
                if 'display_name_override' in provided_fields
                else UNSET
            ),
            email_override=(
                update_data.email_override if 'email_override' in provided_fields else UNSET
            ),
            phone_override=(
                update_data.phone_override if 'phone_override' in provided_fields else UNSET
            ),
            bio=update_data.bio if 'bio' in provided_fields else UNSET,
            is_active=update_data.is_active if 'is_active' in provided_fields else UNSET
        )

        return updated
    except ContextServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/profiles/{user_id}/contexts/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_context_profile(
    user_id: UUID,
    context_id: UUID,
    service: ContextService = Depends(get_context_service),
    _current_user: AuthUser = Depends(require_verified_user)
):
    """Soft-delete a context profile."""
    try:
        context = service.get_context_profile(context_id)
        if context.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Context {context_id} does not belong to user {user_id}"
            )

        service.delete_context_profile(context_id)
        
        return None
    except ContextServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )





