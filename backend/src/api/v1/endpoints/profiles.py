"""
Profile API Endpoints

REST API endpoints for profile management.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies.auth import require_verified_user
from src.core.database import get_db
from src.models.auth import AuthUser
from src.repositories.audit_repository import AuditRepository
from src.repositories.auth_repository import AuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.schemas.profile import (
    IdentityNameCreate,
    IdentityNameResponse,
    IdentityNameUpdate,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from src.services.audit_service import AuditService
from src.services.profile_service import ProfileService, ProfileServiceError

router = APIRouter()


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    """Dependency to get ProfileService instance with audit logging."""
    repository = ProfileRepository(db)
    auth_repo = AuthRepository(db)
    audit_repo = AuditRepository(db)
    audit_service = AuditService(audit_repo)
    return ProfileService(repository, audit_service=audit_service, auth_repository=auth_repo)


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: ProfileCreate, service: ProfileService = Depends(get_profile_service)
):
    """Create a new profile."""
    try:
        profile = service.create_profile(profile_data)
        return profile
    except ProfileServiceError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/profiles/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: UUID, service: ProfileService = Depends(get_profile_service)):
    """Get profile by ID."""
    try:
        profile = service.get_profile(user_id)
        return profile
    except ProfileServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/profiles/{user_id}", response_model=ProfileResponse)
def update_profile(
    user_id: UUID,
    update_data: ProfileUpdate,
    service: ProfileService = Depends(get_profile_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """Update profile fields."""
    try:
        profile = service.update_profile(user_id, update_data)
        response = ProfileResponse.model_validate(profile)
        if getattr(profile, "email_verification_pending", False):
            response.email_verification_pending = True
        return response
    except ProfileServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/profiles/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    user_id: UUID,
    service: ProfileService = Depends(get_profile_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """Soft-delete a profile."""
    try:
        service.delete_profile(user_id)
        return None
    except ProfileServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/profiles/{user_id}/names",
    response_model=IdentityNameResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_identity_name(
    user_id: UUID,
    name_data: IdentityNameCreate,
    service: ProfileService = Depends(get_profile_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """Add an identity name to a profile."""
    try:
        name = service.add_identity_name(user_id, name_data)
        return name
    except ProfileServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/profiles/{user_id}/names", response_model=list[IdentityNameResponse])
def get_identity_names(user_id: UUID, service: ProfileService = Depends(get_profile_service)):
    """Get all identity names for a profile."""
    try:
        profile, names = service.get_profile_with_names(user_id)
        return names
    except ProfileServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/profiles/{user_id}/names/{name_id}", response_model=IdentityNameResponse)
def update_identity_name(
    user_id: UUID,
    name_id: UUID,
    update_data: IdentityNameUpdate,
    service: ProfileService = Depends(get_profile_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """Update an identity name."""
    try:
        name = service.update_identity_name(user_id, name_id, update_data)
        return name
    except ProfileServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/profiles/{user_id}/names/{name_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_identity_name(
    user_id: UUID,
    name_id: UUID,
    service: ProfileService = Depends(get_profile_service),
    _current_user: AuthUser = Depends(require_verified_user),
):
    """Hard-delete an identity name."""
    try:
        service.delete_identity_name(user_id, name_id)
        return None
    except ProfileServiceError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
