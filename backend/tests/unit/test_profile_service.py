"""
Unit Tests for ProfileService
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4

from src.services.profile_service import ProfileService, ProfileServiceError
from src.schemas.profile import ProfileCreate, ProfileUpdate, IdentityNameCreate
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType


@pytest.fixture
def mock_repository():
    return Mock()


@pytest.fixture
def profile_service(mock_repository):
    return ProfileService(mock_repository)


def test_create_verified_with_legal_name(profile_service, mock_repository):
    profile_data = ProfileCreate(
        account_type=AccountType.verified,
        legal_name="John Doe",
        primary_email="john@example.com"
    )
    
    mock_profile = BaseProfile(
        user_id=uuid4(),
        account_type=AccountType.verified,
        legal_name="John Doe",
        primary_email="john@example.com",
        preferred_language="en"
    )
    mock_repository.create_profile.return_value = mock_profile
    mock_repository.get_profile_by_email.return_value = None
    
    result = profile_service.create_profile(profile_data)
    
    assert result.account_type == AccountType.verified


def test_create_verified_without_legal_name_raises_error(profile_service, mock_repository):
    profile_data = ProfileCreate(
        account_type=AccountType.verified,
        legal_name=None,
        primary_email="john@example.com"
    )
    
    mock_repository.get_profile_by_email.return_value = None
    
    with pytest.raises(ProfileServiceError):
        profile_service.create_profile(profile_data)


def test_get_profile_existing(profile_service, mock_repository):
    user_id = uuid4()
    mock_profile = BaseProfile(
        user_id=user_id,
        primary_email="user@example.com",
        preferred_language="en"
    )
    mock_repository.get_profile_by_id.return_value = mock_profile
    
    result = profile_service.get_profile(user_id)
    
    assert result.user_id == user_id


def test_get_profile_nonexistent_raises_error(profile_service, mock_repository):
    mock_repository.get_profile_by_id.return_value = None
    
    with pytest.raises(ProfileServiceError):
        profile_service.get_profile(uuid4())


def test_delete_profile(profile_service, mock_repository):
    user_id = uuid4()
    mock_repository.soft_delete_profile.return_value = True
    
    result = profile_service.delete_profile(user_id)
    
    assert result is True
