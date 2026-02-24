"""Integration tests for database operations."""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel


def test_create_and_query_profile(db_session: Session):
    """Test creating a profile and querying it back"""
    profile = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Test User",
        primary_email="test@example.com",
        preferred_language="en"
    )
    
    db_session.add(profile)
    db_session.commit()


    queried = db_session.query(BaseProfile).filter(
        BaseProfile.primary_email == "test@example.com"
    ).first()
    
    assert queried is not None
    assert queried.legal_name == "Test User"
    assert queried.account_type == AccountType.verified


def test_create_profile_with_names(db_session: Session):
    """Test creating a profile with multiple names"""
    profile = BaseProfile(
        account_type=AccountType.verified,
        primary_email="multi@example.com",
        preferred_language="en"
    )
    
    db_session.add(profile)
    db_session.flush()

    given_name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.given,
        name_value={"en": "John", "es": "Juan"},
        is_primary=True
    )
    
    family_name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.family,
        name_value={"en": "Doe"},
        is_primary=True
    )
    
    db_session.add_all([given_name, family_name])
    db_session.commit()

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
        name_type=NameType.full_name,
        name_value={"zh": "李明", "en": "Li Ming"},
        is_primary=True
    )
    db_session.add(name)
    db_session.commit()

    queried_name = db_session.query(IdentityName).filter(
        IdentityName.identity_id == profile.user_id
    ).first()
    
    assert queried_name.name_value["zh"] == "李明"
    assert queried_name.name_value["en"] == "Li Ming"


def test_soft_delete_filtering(db_session: Session):
    """Test that soft-deleted profiles are filtered out"""
    profile1 = BaseProfile(primary_email="active@example.com")
    profile2 = BaseProfile(primary_email="deleted@example.com")
    
    db_session.add_all([profile1, profile2])
    db_session.commit()
    
    profile2.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    
    active_profiles = db_session.query(BaseProfile).filter(
        BaseProfile.deleted_at.is_(None)
    ).all()
    
    assert len(active_profiles) == 1
    assert active_profiles[0].primary_email == "active@example.com"

    all_profiles = db_session.query(BaseProfile).all()
    assert len(all_profiles) == 2


def test_profile_relationships(db_session: Session):
    """Test bidirectional relationships between profile and names"""
    profile = BaseProfile(primary_email="relationships@example.com")
    db_session.add(profile)
    db_session.flush()
    
    name = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.preferred,
        name_value={"en": "Alex"},
        is_primary=True
    )
    db_session.add(name)
    db_session.commit()
    
    assert profile.identity_names.count() == 1

    queried_name = db_session.query(IdentityName).first()
    assert queried_name.profile.user_id == profile.user_id


def test_account_type_filtering(db_session: Session):
    """Test filtering profiles by account type"""
    verified = BaseProfile(
        account_type=AccountType.verified,
        primary_email="verified@example.com"
    )
    unverified = BaseProfile(
        account_type=AccountType.unverified,
        primary_email="unverified@example.com"
    )
    pseudonymous = BaseProfile(
        account_type=AccountType.pseudonymous,
        primary_email="pseudonymous@example.com"
    )
    
    db_session.add_all([verified, unverified, pseudonymous])
    db_session.commit()
    
    verified_profiles = db_session.query(BaseProfile).filter(
        BaseProfile.account_type == AccountType.verified
    ).all()
    
    assert len(verified_profiles) == 1
    assert verified_profiles[0].primary_email == "verified@example.com"


def test_deprecated_names_filtering(db_session: Session):
    """Test filtering out deprecated names"""
    profile = BaseProfile(primary_email="deprecated@example.com")
    db_session.add(profile)
    db_session.flush()
    
    current = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.preferred,
        name_value={"en": "Jordan"},
        is_primary=True,
        is_deprecated=False
    )
    
    deprecated = IdentityName(
        identity_id=profile.user_id,
        name_type=NameType.given,
        name_value={"en": "[REDACTED]"},
        is_primary=False,
        is_deprecated=True,
        visibility_level=VisibilityLevel.historical_suppressed
    )
    
    db_session.add_all([current, deprecated])
    db_session.commit()
    
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
    db_session.flush()  # Flush instead of commit to work with test fixture transaction
    
    user_id = profile.user_id
    original_email = profile.primary_email
    
    nested = db_session.begin_nested()
    try:
        profile.primary_email = "changed@example.com"
        db_session.flush()
        nested.rollback()
    except Exception:
        nested.rollback()
    
    db_session.expire(profile)

    assert profile.primary_email == original_email

    queried = db_session.query(BaseProfile).filter(
        BaseProfile.user_id == user_id
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
    
    profile2 = BaseProfile(primary_email="unique@example.com")
    db_session.add(profile2)
    
    with pytest.raises(Exception):  # Should raise integrity error
        db_session.commit()
    
    db_session.rollback()

