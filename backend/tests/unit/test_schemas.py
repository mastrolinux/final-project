"""Tests for Profile schema validation and serialization."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.profile import AccountType, NameType, VisibilityLevel
from src.schemas.profile import (
    IdentityNameCreate,
    IdentityNameResponse,
    IdentityNameUpdate,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)


class TestProfileCreate:
    """Test ProfileCreate schema validation"""

    def test_create_profile_with_minimal_fields(self):
        """Test creating profile with only required fields"""
        data = {"primary_email": "user@example.com", "account_type": "unverified"}
        profile = ProfileCreate(**data)

        assert profile.primary_email == "user@example.com"
        assert profile.account_type == AccountType.unverified
        assert profile.preferred_language == "en"  # default value

    def test_create_profile_with_all_fields(self):
        """Test creating profile with all fields"""
        data = {
            "account_type": "verified",
            "legal_name": "John Smith",
            "primary_email": "john@example.com",
            "primary_phone": "+1-555-0101",
            "preferred_language": "es",
        }
        profile = ProfileCreate(**data)

        assert profile.account_type == AccountType.verified
        assert profile.legal_name == "John Smith"
        assert profile.primary_email == "john@example.com"
        assert profile.primary_phone == "+1-555-0101"
        assert profile.preferred_language == "es"

    def test_create_profile_missing_email_raises_error(self):
        """Test that missing email raises validation error"""
        data = {"account_type": "verified"}
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("primary_email",) for e in errors)

    def test_create_profile_invalid_email_raises_error(self):
        """Test that invalid email format raises validation error"""
        data = {"primary_email": "not-an-email", "account_type": "verified"}
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        assert any("email" in str(e).lower() for e in errors)

    def test_create_profile_invalid_account_type_raises_error(self):
        """Test that invalid account type raises validation error"""
        data = {"primary_email": "user@example.com", "account_type": "invalid_type"}
        with pytest.raises(ValidationError):
            ProfileCreate(**data)

    def test_create_profile_empty_legal_name_converts_to_none(self):
        """Test that empty string legal name converts to None"""
        data = {
            "primary_email": "user@example.com",
            "account_type": "pseudonymous",
            "legal_name": "",
        }
        profile = ProfileCreate(**data)
        assert profile.legal_name is None

    def test_create_profile_strips_whitespace(self):
        """Test that email whitespace is stripped"""
        data = {"primary_email": "  user@example.com  ", "account_type": "unverified"}
        profile = ProfileCreate(**data)
        assert profile.primary_email == "user@example.com"


class TestProfileUpdate:
    """Test ProfileUpdate schema validation"""

    def test_update_profile_all_fields_optional(self):
        """Test that all fields are optional for updates"""
        profile = ProfileUpdate()
        assert profile.primary_email is None
        assert profile.account_type is None
        assert profile.legal_name is None

    def test_update_profile_partial_fields(self):
        """Test updating only specific fields"""
        data = {"primary_phone": "+1-555-9999"}
        profile = ProfileUpdate(**data)
        assert profile.primary_phone == "+1-555-9999"
        assert profile.primary_email is None

    def test_update_profile_invalid_email_raises_error(self):
        """Test that invalid email raises validation error"""
        data = {"primary_email": "invalid-email"}
        with pytest.raises(ValidationError):
            ProfileUpdate(**data)

    def test_update_profile_empty_string_converts_to_none(self):
        """Test that empty strings convert to None"""
        data = {"legal_name": "", "primary_phone": ""}
        profile = ProfileUpdate(**data)
        assert profile.legal_name is None
        assert profile.primary_phone is None


class TestProfileResponse:
    """Test ProfileResponse schema serialization"""

    def test_profile_response_serialization(self):
        """Test that response model serializes correctly"""
        data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "account_type": "verified",
            "legal_name": "Jane Doe",
            "primary_email": "jane@example.com",
            "primary_phone": "+1-555-0202",
            "preferred_language": "en",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
            "valid_from": datetime.now(UTC),
            "valid_to": None,
        }
        response = ProfileResponse(**data)

        assert str(response.user_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert response.account_type == AccountType.verified
        assert response.primary_email == "jane@example.com"

    def test_profile_response_excludes_deleted_at_when_none(self):
        """Test that deleted_at is excluded when None"""
        data = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "account_type": "verified",
            "primary_email": "user@example.com",
            "preferred_language": "en",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "deleted_at": None,
            "valid_from": datetime.now(UTC),
            "valid_to": None,
        }
        response = ProfileResponse(**data)
        response_dict = response.model_dump(exclude_none=True)

        assert "deleted_at" not in response_dict


class TestIdentityNameCreate:
    """Test IdentityNameCreate schema validation"""

    def test_create_identity_name_with_required_fields(self):
        """Test creating identity name with required fields"""
        data = {"name_type": "given", "name_value": {"en": "John"}}
        name = IdentityNameCreate(**data)

        assert name.name_type == NameType.given
        assert name.name_value == {"en": "John"}
        assert name.is_primary is False  # default
        assert name.visibility_level == VisibilityLevel.public  # default

    def test_create_identity_name_with_all_fields(self):
        """Test creating identity name with all fields"""
        data = {
            "name_type": "full_name",
            "name_value": {"en": "John Smith", "es": "Juan Smith"},
            "is_primary": True,
            "is_deprecated": False,
            "visibility_level": "public",
        }
        name = IdentityNameCreate(**data)

        assert name.name_type == NameType.full_name
        assert name.name_value == {"en": "John Smith", "es": "Juan Smith"}
        assert name.is_primary is True
        assert name.visibility_level == VisibilityLevel.public

    def test_create_identity_name_missing_name_value_raises_error(self):
        """Test that missing name_value raises error"""
        data = {"name_type": "given"}
        with pytest.raises(ValidationError) as exc_info:
            IdentityNameCreate(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name_value",) for e in errors)

    def test_create_identity_name_empty_name_value_raises_error(self):
        """Test that empty name_value dict raises error"""
        data = {"name_type": "given", "name_value": {}}
        with pytest.raises(ValidationError):
            IdentityNameCreate(**data)

    def test_create_identity_name_invalid_name_type_raises_error(self):
        """Test that invalid name_type raises error"""
        data = {"name_type": "invalid_type", "name_value": {"en": "John"}}
        with pytest.raises(ValidationError):
            IdentityNameCreate(**data)

    def test_create_identity_name_multilingual(self):
        """Test creating multilingual identity name"""
        data = {
            "name_type": "given",
            "name_value": {"en": "Sarah", "zh": "萨拉", "es": "Sara", "ar": "سارة"},
        }
        name = IdentityNameCreate(**data)

        assert len(name.name_value) == 4
        assert name.name_value["zh"] == "萨拉"


class TestIdentityNameUpdate:
    """Test IdentityNameUpdate schema validation"""

    def test_update_identity_name_all_fields_optional(self):
        """Test that all fields are optional for updates"""
        name = IdentityNameUpdate()
        assert name.name_value is None
        assert name.is_primary is None

    def test_update_identity_name_partial_fields(self):
        """Test updating only specific fields"""
        data = {"is_primary": True}
        name = IdentityNameUpdate(**data)
        assert name.is_primary is True
        assert name.name_value is None


class TestIdentityNameResponse:
    """Test IdentityNameResponse schema serialization"""

    def test_identity_name_response_serialization(self):
        """Test that response model serializes correctly"""
        data = {
            "id": "123e4567-e89b-12d3-a456-426614174001",
            "identity_id": "123e4567-e89b-12d3-a456-426614174000",
            "name_type": "full_name",
            "name_value": {"en": "Dr. Sarah Chen"},
            "is_primary": True,
            "is_deprecated": False,
            "visibility_level": "public",
            "context_id": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "valid_from": datetime.now(UTC),
            "valid_to": None,
        }
        response = IdentityNameResponse(**data)

        assert str(response.id) == "123e4567-e89b-12d3-a456-426614174001"
        assert response.name_type == NameType.full_name
        assert response.name_value == {"en": "Dr. Sarah Chen"}
