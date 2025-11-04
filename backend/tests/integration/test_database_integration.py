"""
Integration Tests for Database Operations

Tests database operations with real database interactions.
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel


def test_create_and_query_profile(db_session: Session):
    """Test creating a profile and querying it back"""
    profile = BaseProfile(
        account_type=AccountType.VERIFIED,
        legal_name="Test User",
        primary_email="test@example.com",
        preferred_language="en"
    )
    
    db_session.add(profile)
    db_session.commit()
    
    # Query back
    queried = db_session.query(BaseProfile).filter(
        BaseProfile.primary_email == "test@example.com"
    ).first()
    
    assert queried is not None
    assert queried.legal_name == "Test User"
    assert queried.account_type == AccountType.VERIFIED


def test_create_profile_with_names(db_session: Session):
    """Test creating a profile with multiple names"""
    profile = BaseProfile(
        account_type=AccountType.VERIFIED,
        primary_email="multi@example.com",
        preferred_language="en"
    )
    
    db_session.add(profile)
    db_session.flush()
    
    # Add multiple names
    given_name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.GIVEN,
        name_value={"en": "John", "es": "Juan"},
        is_primary=True
    )
    
    family_name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.FAMILY,
        name_value={"en": "Doe"},
        is_primary=True
    )
    
    db_session.add_all([given_name, family_name])
    db_session.commit()
    
    # Query back with names
    queried = db_session.query(BaseProfile).filter(
        BaseProfile.user_id == profile.user_id
    ).first()
    
    names = queried.identity_names.all()
    assert len(names) == 2


def test_query_jsonb_names(db_session: Session):
    """Test querying JSONB name fields"""
    profile = BaseProfile(
        primary_email="jsonb@example.com",
        preferred_language="zh"
    )
    db_session.add(profile)
    db_session.flush()
    
    name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.FULL_NAME,
        name_value={"zh": "李明", "en": "Li Ming"},
        is_primary=True
    )
    db_session.add(name)
    db_session.commit()
    
    # Query back
    queried_name = db_session.query(IdentityName).filter(
        IdentityName.identity_id == profile.user_id
    ).first()
    
    assert queried_name.name_value["zh"] == "李明"
    assert queried_name.name_value["en"] == "Li Ming"


def test_soft_delete_filtering(db_session: Session):
    """Test that soft-deleted profiles are filtered out"""
    # Create two profiles
    profile1 = BaseProfile(primary_email="active@example.com")
    profile2 = BaseProfile(primary_email="deleted@example.com")
    
    db_session.add_all([profile1, profile2])
    db_session.commit()
    
    # Soft delete one
    profile2.deleted_at = datetime.utcnow()
    db_session.commit()
    
    # Query active profiles
    active_profiles = db_session.query(BaseProfile).filter(
        BaseProfile.deleted_at.is_(None)
    ).all()
    
    assert len(active_profiles) == 1
    assert active_profiles[0].primary_email == "active@example.com"
    
    # Query all profiles (including deleted)
    all_profiles = db_session.query(BaseProfile).all()
    assert len(all_profiles) == 2


def test_profile_relationships(db_session: Session):
    """Test bidirectional relationships between profile and names"""
    profile = BaseProfile(primary_email="relationships@example.com")
    db_session.add(profile)
    db_session.flush()
    
    name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.PREFERRED,
        name_value={"en": "Alex"},
        is_primary=True
    )
    db_session.add(name)
    db_session.commit()
    
    # Test forward relationship (profile -> names)
    assert profile.identity_names.count() == 1
    
    # Test backward relationship (name -> profile)
    queried_name = db_session.query(IdentityName).first()
    assert queried_name.profile.user_id == profile.user_id


def test_account_type_filtering(db_session: Session):
    """Test filtering profiles by account type"""
    verified = BaseProfile(
        account_type=AccountType.VERIFIED,
        primary_email="verified@example.com"
    )
    unverified = BaseProfile(
        account_type=AccountType.UNVERIFIED,
        primary_email="unverified@example.com"
    )
    pseudonymous = BaseProfile(
        account_type=AccountType.PSEUDONYMOUS,
        primary_email="pseudonymous@example.com"
    )
    
    db_session.add_all([verified, unverified, pseudonymous])
    db_session.commit()
    
    # Query by account type
    verified_profiles = db_session.query(BaseProfile).filter(
        BaseProfile.account_type == AccountType.VERIFIED
    ).all()
    
    assert len(verified_profiles) == 1
    assert verified_profiles[0].primary_email == "verified@example.com"


def test_deprecated_names_filtering(db_session: Session):
    """Test filtering out deprecated names"""
    profile = BaseProfile(primary_email="deprecated@example.com")
    db_session.add(profile)
    db_session.flush()
    
    # Current name
    current = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.PREFERRED,
        name_value={"en": "Jordan"},
        is_primary=True,
        is_deprecated=False
    )
    
    # Deprecated name (deadname)
    deprecated = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.GIVEN,
        name_value={"en": "[REDACTED]"},
        is_primary=False,
        is_deprecated=True,
        visibility_level=VisibilityLevel.HISTORICAL_SUPPRESSED
    )
    
    db_session.add_all([current, deprecated])
    db_session.commit()
    
    # Query non-deprecated names
    active_names = db_session.query(IdentityName).filter(
        IdentityName.identity_id == profile.user_id,
        IdentityName.is_deprecated == False
    ).all()
    
    assert len(active_names) == 1
    assert active_names[0].name_value["en"] == "Jordan"


def test_transaction_rollback(db_session: Session):
    """Test transaction rollback on error"""
    profile = BaseProfile(primary_email="rollback@example.com")
    db_session.add(profile)
    db_session.commit()
    
    # Start a new transaction that will fail
    try:
        profile.primary_email = None  # This should violate NOT NULL constraint
        db_session.commit()
    except Exception:
        db_session.rollback()
    
    # Verify original data still exists
    queried = db_session.query(BaseProfile).filter(
        BaseProfile.primary_email == "rollback@example.com"
    ).first()
    
    assert queried is not None
    assert queried.primary_email == "rollback@example.com"


def test_bulk_insert_profiles(db_session: Session):
    """Test bulk inserting multiple profiles"""
    profiles = [
        BaseProfile(primary_email=f"user{i}@example.com")
        for i in range(10)
    ]
    
    db_session.bulk_save_objects(profiles)
    db_session.commit()
    
    count = db_session.query(BaseProfile).count()
    assert count == 10


def test_unique_email_constraint(db_session: Session):
    """Test that duplicate emails are prevented"""
    profile1 = BaseProfile(primary_email="unique@example.com")
    db_session.add(profile1)
    db_session.commit()
    
    # Try to create duplicate
    profile2 = BaseProfile(primary_email="unique@example.com")
    db_session.add(profile2)
    
    with pytest.raises(Exception):  # Should raise integrity error
        db_session.commit()
    
    db_session.rollback()

