"""
Unit Tests for Profile Models

Tests BaseProfile and IdentityName models with their behaviors.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.profile import (
    BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel
)


def test_create_base_profile(db_session: Session):
    """Test creating a BaseProfile"""
    profile = BaseProfile(
        account_type=AccountType.VERIFIED,
        legal_name="John Doe",
        primary_email="john@example.com",
        primary_phone="+1-555-0123",
        preferred_language="en"
    )
    
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    
    assert profile.user_id is not None
    assert profile.account_type == AccountType.VERIFIED
    assert profile.legal_name == "John Doe"
    assert profile.primary_email == "john@example.com"
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_base_profile_defaults(db_session: Session):
    """Test BaseProfile default values"""
    profile = BaseProfile(
        primary_email="test@example.com"
    )
    
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    
    assert profile.account_type == AccountType.UNVERIFIED
    assert profile.preferred_language == "en"
    assert profile.legal_name is None
    assert profile.deleted_at is None


def test_base_profile_soft_delete(db_session: Session, sample_verified_profile: BaseProfile):
    """Test soft delete functionality"""
    assert sample_verified_profile.is_deleted is False
    
    # Soft delete
    sample_verified_profile.deleted_at = datetime.utcnow()
    db_session.commit()
    
    assert sample_verified_profile.is_deleted is True


def test_base_profile_temporal_validity(db_session: Session, sample_verified_profile: BaseProfile):
    """Test temporal validity properties"""
    assert sample_verified_profile.is_valid is True
    assert sample_verified_profile.valid_from is not None
    assert sample_verified_profile.valid_to is None


def test_create_identity_name(db_session: Session, sample_verified_profile: BaseProfile):
    """Test creating an IdentityName"""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.FULL_NAME,
        name_value={"en": "Dr. John Doe"},
        is_primary=True,
        is_deprecated=False,
        visibility_level=VisibilityLevel.PUBLIC
    )
    
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    
    assert name.id is not None
    assert name.identity_id == sample_verified_profile.user_id
    assert name.name_type == NameType.FULL_NAME
    assert name.name_value == {"en": "Dr. John Doe"}
    assert name.is_primary is True


def test_identity_name_relationship(db_session: Session, sample_verified_profile: BaseProfile):
    """Test relationship between BaseProfile and IdentityName"""
    name1 = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.GIVEN,
        name_value={"en": "John"},
        is_primary=True
    )
    name2 = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.FAMILY,
        name_value={"en": "Doe"},
        is_primary=True
    )
    
    db_session.add_all([name1, name2])
    db_session.commit()
    
    # Access relationship
    names = sample_verified_profile.identity_names.all()
    assert len(names) == 2


def test_identity_name_multilingual(db_session: Session, sample_verified_profile: BaseProfile):
    """Test multilingual name storage in JSONB"""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.FULL_NAME,
        name_value={
            "en": "John Doe",
            "es": "Juan Doe",
            "zh": "约翰·多伊",
            "ar": "جون دو"
        },
        is_primary=True
    )
    
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    
    assert name.name_value["en"] == "John Doe"
    assert name.name_value["zh"] == "约翰·多伊"
    assert name.name_value["ar"] == "جون دو"


def test_identity_name_get_name_for_language(db_session: Session, sample_multilingual_name: IdentityName):
    """Test get_name_for_language method"""
    # Request existing language
    assert sample_multilingual_name.get_name_for_language("en") == "Sarah"
    assert sample_multilingual_name.get_name_for_language("zh") == "萨拉"
    
    # Request non-existing language with fallback
    assert sample_multilingual_name.get_name_for_language("fr", fallback="en") == "Sarah"
    
    # Request with no match should return first available
    result = sample_multilingual_name.get_name_for_language("ar", fallback="de")
    assert result in ["Sarah", "萨拉", "Sara"]


def test_identity_name_deprecated(db_session: Session, sample_deprecated_name: IdentityName):
    """Test deprecated name (deadname) handling"""
    assert sample_deprecated_name.is_deprecated is True
    assert sample_deprecated_name.visibility_level == VisibilityLevel.HISTORICAL_SUPPRESSED
    assert sample_deprecated_name.is_primary is False


def test_cascade_delete(db_session: Session, sample_verified_profile: BaseProfile):
    """Test cascade delete from profile to names"""
    # Create names associated with profile
    name1 = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.GIVEN,
        name_value={"en": "John"},
        is_primary=True
    )
    name2 = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.FAMILY,
        name_value={"en": "Doe"},
        is_primary=True
    )
    
    db_session.add_all([name1, name2])
    db_session.commit()
    
    # Verify names exist
    names_count = db_session.query(IdentityName).filter(
        IdentityName.identity_id == sample_verified_profile.user_id
    ).count()
    assert names_count == 2
    
    # Delete profile
    db_session.delete(sample_verified_profile)
    db_session.commit()
    
    # Verify names were cascade deleted
    names_count = db_session.query(IdentityName).filter(
        IdentityName.identity_id == sample_verified_profile.user_id
    ).count()
    assert names_count == 0


def test_account_type_enum():
    """Test AccountType enum values"""
    assert AccountType.VERIFIED.value == "verified"
    assert AccountType.UNVERIFIED.value == "unverified"
    assert AccountType.PSEUDONYMOUS.value == "pseudonymous"


def test_name_type_enum():
    """Test NameType enum values"""
    assert NameType.GIVEN.value == "given"
    assert NameType.FAMILY.value == "family"
    assert NameType.PREFERRED.value == "preferred"
    assert NameType.LEGAL.value == "legal"
    assert NameType.FULL_NAME.value == "full_name"


def test_visibility_level_enum():
    """Test VisibilityLevel enum values"""
    assert VisibilityLevel.PUBLIC.value == "public"
    assert VisibilityLevel.PRIVATE.value == "private"
    assert VisibilityLevel.HISTORICAL_SUPPRESSED.value == "historical_suppressed"

