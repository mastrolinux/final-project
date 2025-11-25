"""
Unit Tests for ProfileRepository

Tests data access layer methods for Profile and IdentityName entities.
Following TDD approach - these tests will initially fail.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.repositories.profile_repository import ProfileRepository
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel


class TestProfileRepositoryCreate:
    """Test profile creation methods"""
    
    def test_create_profile(self, db_session):
        """Test creating a basic profile"""
        repo = ProfileRepository(db_session)
        
        profile_data = {
            "account_type": AccountType.verified,
            "legal_name": "John Doe",
            "primary_email": "john@example.com",
            "preferred_language": "en"
        }
        
        profile = repo.create_profile(**profile_data)
        
        assert profile.user_id is not None
        assert profile.account_type == AccountType.verified
        assert profile.legal_name == "John Doe"
        assert profile.primary_email == "john@example.com"
        assert profile.created_at is not None
    
    def test_create_profile_generates_uuid(self, db_session):
        """Test that profile creation generates a UUID"""
        repo = ProfileRepository(db_session)
        
        profile = repo.create_profile(
            account_type=AccountType.unverified,
            primary_email="user@example.com",
            preferred_language="en"
        )
        
        assert profile.user_id is not None
        assert len(str(profile.user_id)) == 36  # UUID format
    
    def test_create_profile_sets_timestamps(self, db_session):
        """Test that profile creation sets created_at and updated_at"""
        repo = ProfileRepository(db_session)
        
        profile = repo.create_profile(
            account_type=AccountType.pseudonymous,
            primary_email="anon@example.com",
            preferred_language="en"
        )
        
        assert profile.created_at is not None
        assert profile.updated_at is not None
        assert profile.valid_from is not None


class TestProfileRepositoryRead:
    """Test profile retrieval methods"""
    
    def test_get_profile_by_id_existing(self, db_session, sample_verified_profile):
        """Test retrieving an existing profile by ID"""
        repo = ProfileRepository(db_session)
        
        profile = repo.get_profile_by_id(sample_verified_profile.user_id)
        
        assert profile is not None
        assert profile.user_id == sample_verified_profile.user_id
        assert profile.primary_email == sample_verified_profile.primary_email
    
    def test_get_profile_by_id_nonexistent(self, db_session):
        """Test retrieving a nonexistent profile returns None"""
        repo = ProfileRepository(db_session)
        
        profile = repo.get_profile_by_id(uuid4())
        
        assert profile is None
    
    def test_get_profile_by_email_existing(self, db_session, sample_verified_profile):
        """Test retrieving a profile by email"""
        repo = ProfileRepository(db_session)
        
        profile = repo.get_profile_by_email(sample_verified_profile.primary_email)
        
        assert profile is not None
        assert profile.user_id == sample_verified_profile.user_id
        assert profile.primary_email == sample_verified_profile.primary_email
    
    def test_get_profile_by_email_nonexistent(self, db_session):
        """Test retrieving nonexistent email returns None"""
        repo = ProfileRepository(db_session)
        
        profile = repo.get_profile_by_email("nonexistent@example.com")
        
        assert profile is None
    
    def test_get_profile_by_email_case_sensitive(self, db_session, sample_verified_profile):
        """Test email lookup is case-sensitive"""
        repo = ProfileRepository(db_session)
        
        # Email stored as lowercase
        profile = repo.get_profile_by_email(sample_verified_profile.primary_email.upper())
        
        # Should still find it if database handles case-insensitivity
        # Or should not find it if case-sensitive
        # This test documents the behavior
        assert profile is None or profile.user_id == sample_verified_profile.user_id
    
    def test_list_profiles_empty(self, db_session):
        """Test listing profiles when database is empty"""
        repo = ProfileRepository(db_session)
        
        profiles = repo.list_profiles()
        
        assert profiles == []
    
    def test_list_profiles_multiple(self, db_session, sample_profiles_with_names):
        """Test listing all profiles"""
        repo = ProfileRepository(db_session)
        
        profiles = repo.list_profiles()
        
        assert len(profiles) == 3
        assert all(isinstance(p, BaseProfile) for p in profiles)
    
    def test_list_profiles_with_pagination(self, db_session, sample_profiles_with_names):
        """Test listing profiles with limit and offset"""
        repo = ProfileRepository(db_session)
        
        profiles = repo.list_profiles(limit=2, offset=0)
        assert len(profiles) == 2
        
        profiles = repo.list_profiles(limit=2, offset=2)
        assert len(profiles) == 1
    
    def test_list_profiles_excludes_deleted(self, db_session, sample_verified_profile):
        """Test that soft-deleted profiles are excluded from listing"""
        repo = ProfileRepository(db_session)
        
        # Soft delete the profile
        repo.soft_delete_profile(sample_verified_profile.user_id)
        
        # Should not appear in list
        profiles = repo.list_profiles()
        assert len(profiles) == 0


class TestProfileRepositoryUpdate:
    """Test profile update methods"""
    
    def test_update_profile(self, db_session, sample_verified_profile):
        """Test updating profile fields"""
        repo = ProfileRepository(db_session)
        
        updated_profile = repo.update_profile(
            sample_verified_profile.user_id,
            primary_phone="+1-555-9999",
            preferred_language="es"
        )
        
        assert updated_profile.primary_phone == "+1-555-9999"
        assert updated_profile.preferred_language == "es"
        # Should preserve other fields
        assert updated_profile.primary_email == sample_verified_profile.primary_email
    
    def test_update_profile_updates_timestamp(self, db_session, sample_verified_profile):
        """Test that update changes updated_at timestamp"""
        repo = ProfileRepository(db_session)
        
        original_updated_at = sample_verified_profile.updated_at
        
        updated_profile = repo.update_profile(
            sample_verified_profile.user_id,
            preferred_language="fr"
        )
        
        assert updated_profile.updated_at > original_updated_at
    
    def test_update_nonexistent_profile_returns_none(self, db_session):
        """Test updating nonexistent profile returns None"""
        repo = ProfileRepository(db_session)
        
        result = repo.update_profile(
            uuid4(),
            preferred_language="de"
        )
        
        assert result is None
    
    def test_update_profile_with_no_changes(self, db_session, sample_verified_profile):
        """Test updating profile with no actual changes"""
        repo = ProfileRepository(db_session)
        
        updated_profile = repo.update_profile(sample_verified_profile.user_id)
        
        assert updated_profile.user_id == sample_verified_profile.user_id


class TestProfileRepositorySoftDelete:
    """Test soft delete functionality"""
    
    def test_soft_delete_profile(self, db_session, sample_verified_profile):
        """Test soft deleting a profile"""
        repo = ProfileRepository(db_session)
        
        result = repo.soft_delete_profile(sample_verified_profile.user_id)
        
        assert result is True
        
        # Profile should still exist but marked deleted
        profile = db_session.query(BaseProfile).filter(
            BaseProfile.user_id == sample_verified_profile.user_id
        ).first()
        
        assert profile is not None
        assert profile.deleted_at is not None
    
    def test_soft_delete_nonexistent_profile(self, db_session):
        """Test soft deleting nonexistent profile returns False"""
        repo = ProfileRepository(db_session)
        
        result = repo.soft_delete_profile(uuid4())
        
        assert result is False
    
    def test_soft_deleted_profile_not_retrieved_by_id(self, db_session, sample_verified_profile):
        """Test that soft-deleted profiles are not retrieved by get_profile_by_id"""
        repo = ProfileRepository(db_session)
        
        repo.soft_delete_profile(sample_verified_profile.user_id)
        
        profile = repo.get_profile_by_id(sample_verified_profile.user_id)
        
        assert profile is None
    
    def test_soft_deleted_profile_not_retrieved_by_email(self, db_session, sample_verified_profile):
        """Test that soft-deleted profiles are not retrieved by get_profile_by_email"""
        repo = ProfileRepository(db_session)
        
        repo.soft_delete_profile(sample_verified_profile.user_id)
        
        profile = repo.get_profile_by_email(sample_verified_profile.primary_email)
        
        assert profile is None


class TestIdentityNameRepository:
    """Test identity name CRUD operations"""
    
    def test_create_identity_name(self, db_session, sample_verified_profile):
        """Test creating an identity name"""
        repo = ProfileRepository(db_session)
        
        name_data = {
            "identity_id": sample_verified_profile.user_id,
            "name_type": NameType.full_name,
            "name_value": {"en": "Dr. John Doe", "es": "Dr. Juan Doe"},
            "is_primary": True,
            "visibility_level": VisibilityLevel.public
        }
        
        name = repo.create_identity_name(**name_data)
        
        assert name.id is not None
        assert name.identity_id == sample_verified_profile.user_id
        assert name.name_type == NameType.full_name
        assert name.name_value == {"en": "Dr. John Doe", "es": "Dr. Juan Doe"}
        assert name.is_primary is True
    
    def test_get_identity_names_for_profile(self, db_session, sample_verified_profile, sample_identity_name):
        """Test retrieving all identity names for a profile"""
        repo = ProfileRepository(db_session)
        
        names = repo.get_identity_names(sample_verified_profile.user_id)
        
        assert len(names) >= 1
        assert all(isinstance(n, IdentityName) for n in names)
        assert all(n.identity_id == sample_verified_profile.user_id for n in names)
    
    def test_get_identity_names_empty_profile(self, db_session, sample_verified_profile):
        """Test getting identity names for profile with no names"""
        repo = ProfileRepository(db_session)
        
        names = repo.get_identity_names(sample_verified_profile.user_id)
        
        # Profile from fixture has no names by default
        assert names == []
    
    def test_get_identity_name_by_id(self, db_session, sample_identity_name):
        """Test retrieving a specific identity name by ID"""
        repo = ProfileRepository(db_session)
        
        name = repo.get_identity_name_by_id(sample_identity_name.id)
        
        assert name is not None
        assert name.id == sample_identity_name.id
    
    def test_update_identity_name(self, db_session, sample_identity_name):
        """Test updating an identity name"""
        repo = ProfileRepository(db_session)
        
        updated_name = repo.update_identity_name(
            sample_identity_name.id,
            is_primary=False,
            visibility_level=VisibilityLevel.private
        )
        
        assert updated_name.is_primary is False
        assert updated_name.visibility_level == VisibilityLevel.private
    
    def test_delete_identity_name(self, db_session, sample_identity_name):
        """Test deleting an identity name"""
        repo = ProfileRepository(db_session)
        
        result = repo.delete_identity_name(sample_identity_name.id)
        
        assert result is True
        
        # Should no longer exist
        name = repo.get_identity_name_by_id(sample_identity_name.id)
        assert name is None


class TestProfileWithNames:
    """Test retrieving profiles with associated names"""
    
    def test_get_profile_with_names(self, db_session, sample_verified_profile, sample_identity_name):
        """Test retrieving profile with all identity names"""
        repo = ProfileRepository(db_session)
        
        profile, names = repo.get_profile_with_names(sample_verified_profile.user_id)
        
        assert profile is not None
        assert profile.user_id == sample_verified_profile.user_id
        assert len(names) >= 1
        assert all(n.identity_id == sample_verified_profile.user_id for n in names)
    
    def test_get_profile_with_names_no_names(self, db_session, sample_verified_profile):
        """Test retrieving profile with no names"""
        repo = ProfileRepository(db_session)
        
        profile, names = repo.get_profile_with_names(sample_verified_profile.user_id)
        
        assert profile is not None
        assert names == []
    
    def test_get_profile_with_names_nonexistent(self, db_session):
        """Test retrieving nonexistent profile returns None"""
        repo = ProfileRepository(db_session)
        
        profile, names = repo.get_profile_with_names(uuid4())
        
        assert profile is None
        assert names == []

