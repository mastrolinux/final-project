"""
Context Profile API Endpoints

REST API endpoints for context profile management.
Implements multi-context identity presentation based on Goffman's dramaturgical theory.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.context_service import ContextService, ContextServiceError
from src.schemas.context import (
    ContextProfileCreate,
    ContextProfileUpdate,
    ContextProfileResponse,
    ResolvedProfileResponse
)


router = APIRouter()


def get_context_service(db: Session = Depends(get_db)) -> ContextService:
    """Dependency to get ContextService instance"""
    context_repo = ContextRepository(db)
    profile_repo = ProfileRepository(db)
    return ContextService(context_repo, profile_repo)


@router.post(
    "/profiles/{user_id}/contexts",
    response_model=ContextProfileResponse,
    status_code=status.HTTP_201_CREATED
)
def create_context_profile(
    user_id: UUID,
    context_data: ContextProfileCreate,
    service: ContextService = Depends(get_context_service)
):
    """
    Create a new context profile for a user
    
    Enables users to present different identity aspects in different social contexts.
    
    - **context_type**: professional, social, legal, or healthcare
    - **context_name**: User-defined label (e.g., "LinkedIn", "Family Photos")
    - **display_name_override**: Optional override for display name
    - **email_override**: Optional override for email
    - **phone_override**: Optional override for phone
    - **bio**: Optional context-specific biography
    
    **Business Rules:**
    - Pseudonymous accounts cannot create legal or healthcare contexts
    - Context (user_id, context_type, context_name) must be unique
    
    **Example Use Case:**
    Privacy-focused professional creates professional context with work credentials
    while keeping personal information private from career platforms.
    """
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
        elif "cannot create" in str(e).lower():
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
    """
    List all context profiles for a user
    
    Returns raw context profiles showing only overrides.
    Use the resolved endpoint to see the full merged profile.
    
    - **include_inactive**: Whether to include inactive contexts
    """
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
    """
    Get a specific context profile (raw overrides only)
    
    Returns the context profile showing only override fields.
    Use the /resolved endpoint to see the full merged profile.
    """
    try:
        context = service.get_context_profile(context_id)
        
        # Verify context belongs to user
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
    language: str = Query(
        default="en",
        description="Language code for name resolution (ISO 639-1)"
    ),
    include_deprecated: bool = Query(
        default=False,
        description="Include deprecated names in results"
    ),
    service: ContextService = Depends(get_context_service)
):
    """
    Get fully resolved profile with context inheritance applied
    
    **CRITICAL ENDPOINT: Demonstrates the inheritance engine**
    
    This endpoint implements Goffman's dramaturgical theory by merging:
    1. Base profile fields
    2. Context-specific overrides
    3. Multilingual name resolution
    
    The resolved profile is what third-party applications receive via OAuth.
    
    **Inheritance Rules:**
    - Start with base profile values
    - Apply context overrides (null overrides inherit from base)
    - Filter deprecated names unless explicitly requested
    - Resolve multilingual names using language preference
    
    **Example:**
    - Base profile: email=personal@example.com, phone=+1-555-1234
    - Professional context: email_override=work@company.com, phone_override=None
    - Resolved: email=work@company.com, phone=+1-555-1234 (inherited)
    """
    try:
        resolved = service.resolve_context_profile(
            user_id=user_id,
            context_id=context_id,
            language=language,
            include_deprecated_names=include_deprecated
        )
        
        # Convert ResolvedProfile to dict for Pydantic response
        return ResolvedProfileResponse(
            user_id=resolved.user_id,
            account_type=resolved.account_type,
            display_name=resolved.display_name,
            email=resolved.email,
            phone=resolved.phone,
            preferred_language=resolved.preferred_language,
            bio=resolved.bio,
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
        if "not found" in str(e).lower():
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
    language: str = Query(
        default="en",
        description="Language code for name resolution (ISO 639-1)"
    ),
    include_deprecated: bool = Query(
        default=False,
        description="Include deprecated names in results"
    ),
    service: ContextService = Depends(get_context_service)
):
    """
    Get resolved base profile without context overrides
    
    Returns the user's default identity presentation without any context-specific overrides.
    Useful for displaying the user's primary profile.
    """
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
    service: ContextService = Depends(get_context_service)
):
    """
    Update a context profile
    
    Allows partial updates to context overrides.
    Setting a field to null removes the override (inherits from base profile).
    """
    try:
        # Verify context belongs to user first
        context = service.get_context_profile(context_id)
        if context.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Context {context_id} does not belong to user {user_id}"
            )
        
        # Update context
        updated = service.update_context_profile(
            context_id=context_id,
            display_name_override=update_data.display_name_override,
            email_override=update_data.email_override,
            phone_override=update_data.phone_override,
            bio=update_data.bio,
            is_active=update_data.is_active
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
    service: ContextService = Depends(get_context_service)
):
    """
    Delete a context profile (soft delete)
    
    Marks the context as deleted without physically removing it.
    The context can be recovered within the retention period.
    """
    try:
        # Verify context belongs to user first
        context = service.get_context_profile(context_id)
        if context.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Context {context_id} does not belong to user {user_id}"
            )
        
        # Delete context
        service.delete_context_profile(context_id)
        
        return None
    except ContextServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

