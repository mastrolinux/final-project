"""
Test Data Factories using factory_boy + Faker

Provides factories for generating test data for all models.
Integrates Faker for realistic, culturally-diverse data generation.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

import factory
from factory import Faker as FactoryFaker
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from src.models.profile import (
    BaseProfile,
    IdentityName,
    AccountType,
    NameType,
    VisibilityLevel,
)


# Initialize Faker with multiple locales for diverse name generation
fake = Faker()
fake_zh = Faker('zh_CN')
fake_es = Faker('es_ES')
fake_ar = Faker('ar_SA')
fake_id = Faker('id_ID')


class BaseProfileFactory(SQLAlchemyModelFactory):
    """
    Factory for BaseProfile model.
    
    Generates diverse profiles with realistic data.
    Can be customized for different account types and cultural contexts.
    
    Usage:
        # Create instance (doesn't save to DB)
        profile = BaseProfileFactory.build()
        
        # Create and save to database
        profile = BaseProfileFactory.create(session=db_session)
        
        # Create specific account type
        verified_profile = BaseProfileFactory.build(account_type=AccountType.verified)
    """
    
    class Meta:
        model = BaseProfile
        sqlalchemy_session = None  # Set in conftest.py
        sqlalchemy_session_persistence = None  # Don't auto-commit
    
    user_id = factory.LazyFunction(uuid.uuid4)
    account_type = AccountType.verified
    legal_name = FactoryFaker('name')
    primary_email = factory.Sequence(lambda n: f'user{n}@example.com')
    primary_phone = FactoryFaker('phone_number')
    preferred_language = "en"


class VerifiedProfileFactory(BaseProfileFactory):
    """Factory for verified profiles with legal name"""
    account_type = AccountType.verified
    legal_name = FactoryFaker('name')


class UnverifiedProfileFactory(BaseProfileFactory):
    """Factory for unverified profiles without legal name"""
    account_type = AccountType.unverified
    legal_name = None


class PseudonymousProfileFactory(BaseProfileFactory):
    """Factory for pseudonymous profiles with privacy focus"""
    account_type = AccountType.pseudonymous
    legal_name = None
    primary_phone = None


class IdentityNameFactory(SQLAlchemyModelFactory):
    """
    Factory for IdentityName model.
    
    Generates multilingual names with realistic data.
    Supports diverse cultural naming conventions.
    
    Usage:
        # Create with default English name
        name = IdentityNameFactory.build()
        
        # Create multilingual name
        name = IdentityNameFactory.build(
            name_value={"en": "Sarah", "zh": "萨拉", "es": "Sara"}
        )
        
        # Create with specific profile
        name = IdentityNameFactory.build(identity_id=profile.user_id)
    """
    
    class Meta:
        model = IdentityName
        sqlalchemy_session = None  # Set in conftest.py
        sqlalchemy_session_persistence = None  # Don't auto-commit
    
    id = factory.LazyFunction(uuid.uuid4)
    identity_id = factory.LazyFunction(uuid.uuid4)  # Override in usage
    name_type = NameType.full_name
    
    # Simple English name by default - factory_boy handles JSONB correctly!
    name_value = factory.LazyFunction(lambda: {"en": fake.name()})
    
    is_primary = True
    is_deprecated = False
    visibility_level = VisibilityLevel.public
    context_id = None


class WesternNameFactory(IdentityNameFactory):
    """Factory for Western naming convention (given + family)"""
    name_type = NameType.full_name
    name_value = factory.LazyFunction(lambda: {"en": fake.name()})


class ChineseNameFactory(IdentityNameFactory):
    """
    Factory for Chinese naming convention.
    
    Generates names in Chinese characters with romanization.
    """
    name_type = NameType.full_name
    name_value = factory.LazyFunction(lambda: {
        "zh": fake_zh.name(),
        "en": fake_zh.name()
    })


class MultilingualNameFactory(IdentityNameFactory):
    """
    Factory for multilingual names.
    
    Generates names in multiple languages (English, Chinese, Spanish).
    """
    name_type = NameType.given
    name_value = factory.LazyFunction(lambda: {
        "en": fake.first_name(),
        "zh": fake_zh.first_name(),
        "es": fake_es.first_name()
    })


class MononymFactory(IdentityNameFactory):
    """
    Factory for mononym (single name) convention.
    
    Common in Indonesian and other cultures.
    """
    name_type = NameType.full_name
    name_value = factory.LazyFunction(lambda: {
        "id": fake_id.first_name(),
        "en": fake_id.first_name()
    })


class DeprecatedNameFactory(IdentityNameFactory):
    """
    Factory for deprecated names (deadnames).
    
    Creates historical names with suppressed visibility.
    """
    name_type = NameType.given
    name_value = factory.LazyFunction(lambda: {"en": "[REDACTED]"})
    is_primary = False
    is_deprecated = True
    visibility_level = VisibilityLevel.historical_suppressed


class GivenNameFactory(IdentityNameFactory):
    """Factory for given names (first names)"""
    name_type = NameType.given
    name_value = factory.LazyFunction(lambda: {"en": fake.first_name()})


class FamilyNameFactory(IdentityNameFactory):
    """Factory for family names (last names)"""
    name_type = NameType.family
    name_value = factory.LazyFunction(lambda: {"en": fake.last_name()})


class PreferredNameFactory(IdentityNameFactory):
    """Factory for preferred names (nicknames, chosen names)"""
    name_type = NameType.preferred
    name_value = factory.LazyFunction(lambda: {"en": fake.first_name()})


# Utility functions for complex test scenarios

def create_profile_with_names(
    session: Any,
    account_type: AccountType = AccountType.verified,
    num_names: int = 2
) -> tuple[BaseProfile, list[IdentityName]]:
    """
    Create a profile with multiple associated names.
    
    Args:
        session: Database session
        account_type: Type of account to create
        num_names: Number of names to create (default: 2)
        
    Returns:
        Tuple of (profile, list of names)
    """
    factory_map = {
        AccountType.verified: VerifiedProfileFactory,
        AccountType.unverified: UnverifiedProfileFactory,
        AccountType.pseudonymous: PseudonymousProfileFactory,
    }
    
    factory_class = factory_map.get(account_type, BaseProfileFactory)
    profile = factory_class.build()
    session.add(profile)
    session.flush()
    
    names = []
    for i in range(num_names):
        name_factory = GivenNameFactory if i == 0 else FamilyNameFactory
        name = name_factory.build(
            identity_id=profile.user_id,
            is_primary=(i == 0)
        )
        session.add(name)
        names.append(name)
    
    session.commit()
    session.refresh(profile)
    for name in names:
        session.refresh(name)
    
    return profile, names


def create_diverse_profiles(session: Any) -> list[BaseProfile]:
    """
    Create a diverse set of profiles demonstrating cultural inclusivity.
    
    Includes:
    - Western naming (English)
    - Chinese naming with romanization
    - Mononym (Indonesian)
    - Pseudonymous profile
    - Profile with name change (deprecated name)
    
    Args:
        session: Database session
        
    Returns:
        List of created profiles
    """
    profiles = []
    
    # Western profile
    western_profile = VerifiedProfileFactory.build(
        legal_name="Sarah Elizabeth Chen",
        primary_email="sarah.chen@example.com",
        preferred_language="en"
    )
    session.add(western_profile)
    session.flush()
    
    western_name = WesternNameFactory.build(
        identity_id=western_profile.user_id,
        name_value={"en": "Sarah Chen"}
    )
    session.add(western_name)
    profiles.append(western_profile)
    
    # Chinese profile
    chinese_profile = UnverifiedProfileFactory.build(
        primary_email="li.ming@example.com",
        preferred_language="zh"
    )
    session.add(chinese_profile)
    session.flush()
    
    chinese_name = ChineseNameFactory.build(
        identity_id=chinese_profile.user_id
    )
    session.add(chinese_name)
    profiles.append(chinese_profile)
    
    # Mononym profile
    mononym_profile = VerifiedProfileFactory.build(
        legal_name="Sukarno",
        primary_email="sukarno@example.id",
        preferred_language="id"
    )
    session.add(mononym_profile)
    session.flush()
    
    mononym_name = MononymFactory.build(
        identity_id=mononym_profile.user_id
    )
    session.add(mononym_name)
    profiles.append(mononym_profile)
    
    # Pseudonymous profile
    pseudonymous_profile = PseudonymousProfileFactory.build(
        primary_email="anonymous@protonmail.com",
        preferred_language="en"
    )
    session.add(pseudonymous_profile)
    session.flush()
    
    pseudo_name = PreferredNameFactory.build(
        identity_id=pseudonymous_profile.user_id,
        name_value={"en": "Alex"}
    )
    session.add(pseudo_name)
    profiles.append(pseudonymous_profile)
    
    session.commit()
    for profile in profiles:
        session.refresh(profile)
    
    return profiles
