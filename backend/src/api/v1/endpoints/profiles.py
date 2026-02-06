"""
Profile API Endpoints

REST API endpoints for profile management.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.repositories.profile_repository import ProfileRepository
from src.repositories.audit_repository import AuditRepository
from src.services.profile_service import ProfileService, ProfileServiceError
from src.services.audit_service import AuditService
from src.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    IdentityNameCreate,
    IdentityNameUpdate,
    IdentityNameResponse
)


router = APIRouter()


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    """Dependency to get ProfileService instance with audit logging."""
    repository = ProfileRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return ProfileService(repository, audit_service=audit_service)


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Create a new profile
    
    - **account_type**: verified, unverified, or pseudonymous
    - **legal_name**: Required for verified accounts
    - **primary_email**: Must be unique
    """
    try:
        profile = service.create_profile(profile_data)
        return profile
    except ProfileServiceError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/profiles/{user_id}", response_model=ProfileResponse)
def get_profile(
    user_id: UUID,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Get profile by ID
    
    Returns profile details excluding soft-deleted profiles.
    """
    try:
        profile = service.get_profile(user_id)
        return profile
    except ProfileServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/profiles/{user_id}", response_model=ProfileResponse)
def update_profile(
    user_id: UUID,
    update_data: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Update profile fields
    
    Validates business rules:
    - Verified accounts require legal_name
    - Cannot downgrade from verified account type
    - Email must be unique
    """
    try:
        profile = service.update_profile(user_id, update_data)
        return profile
    except ProfileServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/profiles/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    user_id: UUID,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Soft delete a profile
    
    Sets deleted_at timestamp. Profile will no longer appear in queries.
    """
    try:
        service.delete_profile(user_id)
        return None
    except ProfileServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/profiles/{user_id}/names",
    response_model=IdentityNameResponse,
    status_code=status.HTTP_201_CREATED
)
def add_identity_name(
    user_id: UUID,
    name_data: IdentityNameCreate,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Add an identity name to a profile
    
    Supports multilingual names with JSONB storage.
    """
    try:
        name = service.add_identity_name(user_id, name_data)
        return name
    except ProfileServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/profiles/{user_id}/names", response_model=List[IdentityNameResponse])
def get_identity_names(
    user_id: UUID,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Get all identity names for a profile
    
    Returns list of identity names, excluding deprecated names by default.
    """
    try:
        profile, names = service.get_profile_with_names(user_id)
        return names
    except ProfileServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch(
    "/profiles/{user_id}/names/{name_id}",
    response_model=IdentityNameResponse
)
def update_identity_name(
    user_id: UUID,
    name_id: UUID,
    update_data: IdentityNameUpdate,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Update an identity name

    Validates that the name belongs to the specified user.
    Only provided (non-null) fields are updated.
    """
    try:
        name = service.update_identity_name(user_id, name_id, update_data)
        return name
    except ProfileServiceError as e:
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
    "/profiles/{user_id}/names/{name_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_identity_name(
    user_id: UUID,
    name_id: UUID,
    service: ProfileService = Depends(get_profile_service)
):
    """
    Delete an identity name

    Hard deletes the name record. Validates ownership before deletion.
    """
    try:
        service.delete_identity_name(user_id, name_id)
        return None
    except ProfileServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

