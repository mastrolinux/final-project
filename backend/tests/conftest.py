"""
Pytest Configuration and Fixtures

Provides reusable test fixtures for database, client, and sample data.
Ensures test isolation and cleanup between tests.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.main import app
from src.core.database import Base, get_db
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel


# Use in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_engine():
    """
    Create a test database engine.
    
    Uses SQLite in-memory database with StaticPool for fast tests.
    Scope is 'function' to ensure isolation between tests.
    """
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create a database session for testing.
    
    Provides a clean database session that is rolled back after each test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    # Only rollback if transaction is still active
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with overridden database dependency.
    
    All database operations in the API will use the test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# Sample data fixtures

@pytest.fixture
def sample_verified_profile(db_session: Session) -> BaseProfile:
    """Create a sample verified profile for testing"""
    profile = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Sarah Elizabeth Chen",
        primary_email="sarah.chen@example.com",
        primary_phone="+1-555-0101",
        preferred_language="en"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_unverified_profile(db_session: Session) -> BaseProfile:
    """Create a sample unverified profile for testing"""
    profile = BaseProfile(
        account_type=AccountType.unverified,
        legal_name=None,
        primary_email="john.doe@example.com",
        primary_phone="+1-555-0202",
        preferred_language="en"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_pseudonymous_profile(db_session: Session) -> BaseProfile:
    """Create a sample pseudonymous profile for testing"""
    profile = BaseProfile(
        account_type=AccountType.pseudonymous,
        legal_name=None,
        primary_email="anonymous@protonmail.com",
        primary_phone=None,
        preferred_language="en"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_identity_name(db_session: Session, sample_verified_profile: BaseProfile) -> IdentityName:
    """Create a sample identity name for testing"""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.full_name,
        name_value={"en": "Dr. Sarah Chen"},
        is_primary=True,
        is_deprecated=False,
        visibility_level=VisibilityLevel.public
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_multilingual_name(db_session: Session, sample_verified_profile: BaseProfile) -> IdentityName:
    """Create a sample multilingual identity name for testing"""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.given,
        name_value={
            "en": "Sarah",
            "zh": "萨拉",
            "es": "Sara"
        },
        is_primary=True,
        is_deprecated=False,
        visibility_level=VisibilityLevel.public
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_deprecated_name(db_session: Session, sample_verified_profile: BaseProfile) -> IdentityName:
    """Create a sample deprecated (deadname) for testing"""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.given,
        name_value={"en": "[REDACTED]"},
        is_primary=False,
        is_deprecated=True,
        visibility_level=VisibilityLevel.historical_suppressed
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_profiles_with_names(db_session: Session) -> list[BaseProfile]:
    """Create multiple profiles with associated names for testing"""
    profiles = []
    
    # Profile 1: Western naming
    profile1 = BaseProfile(
        account_type=AccountType.verified,
        legal_name="John Smith",
        primary_email="john.smith@example.com",
        preferred_language="en"
    )
    db_session.add(profile1)
    db_session.flush()
    
    name1 = IdentityName(
        identity_id=profile1.user_id,
        name_type=NameType.full_name,
        name_value={"en": "John Smith"},
        is_primary=True
    )
    db_session.add(name1)
    profiles.append(profile1)
    
    # Profile 2: Chinese naming
    profile2 = BaseProfile(
        account_type=AccountType.unverified,
        primary_email="li.ming@example.com",
        preferred_language="zh"
    )
    db_session.add(profile2)
    db_session.flush()
    
    name2 = IdentityName(
        identity_id=profile2.user_id,
        name_type=NameType.full_name,
        name_value={"zh": "李明", "en": "Li Ming"},
        is_primary=True
    )
    db_session.add(name2)
    profiles.append(profile2)
    
    # Profile 3: Mononym
    profile3 = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Sukarno",
        primary_email="sukarno@example.id",
        preferred_language="id"
    )
    db_session.add(profile3)
    db_session.flush()
    
    name3 = IdentityName(
        identity_id=profile3.user_id,
        name_type=NameType.full_name,
        name_value={"id": "Sukarno", "en": "Sukarno"},
        is_primary=True
    )
    db_session.add(name3)
    profiles.append(profile3)
    
    db_session.commit()
    for profile in profiles:
        db_session.refresh(profile)
    
    return profiles

