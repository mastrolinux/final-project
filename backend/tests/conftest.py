"""Test fixtures for database, client, and sample data."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database import Base, get_db
from src.core.security import create_access_token
from src.main import app
from src.models.auth import AuthUser
from src.models.profile import AccountType, BaseProfile, IdentityName, NameType, VisibilityLevel
from src.repositories.audit_repository import AuditRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.audit_service import AuditService
from src.services.profile_service import ProfileService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """In-memory SQLite engine with StaticPool, recreated per test."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Database session rolled back after each test."""
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
    """FastAPI test client using the test database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_verified_profile(db_session: Session) -> BaseProfile:
    """Verified profile fixture."""
    profile = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Sarah Elizabeth Chen",
        primary_email="sarah.chen@example.com",
        primary_phone="+1-555-0101",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_unverified_profile(db_session: Session) -> BaseProfile:
    """Unverified profile fixture."""
    profile = BaseProfile(
        account_type=AccountType.unverified,
        legal_name=None,
        primary_email="john.doe@example.com",
        primary_phone="+1-555-0202",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_pseudonymous_profile(db_session: Session) -> BaseProfile:
    """Pseudonymous profile fixture."""
    profile = BaseProfile(
        account_type=AccountType.pseudonymous,
        legal_name=None,
        primary_email="anonymous@protonmail.com",
        primary_phone=None,
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_identity_name(db_session: Session, sample_verified_profile: BaseProfile) -> IdentityName:
    """English full_name identity name for the verified profile."""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.full_name,
        name_value={"en": "Dr. Sarah Chen"},
        is_primary=True,
        is_deprecated=False,
        visibility_level=VisibilityLevel.public,
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_multilingual_name(
    db_session: Session, sample_verified_profile: BaseProfile
) -> IdentityName:
    """Multilingual (en/zh/es) given name for the verified profile."""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.given,
        name_value={"en": "Sarah", "zh": "萨拉", "es": "Sara"},
        is_primary=True,
        is_deprecated=False,
        visibility_level=VisibilityLevel.public,
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_deprecated_name(
    db_session: Session, sample_verified_profile: BaseProfile
) -> IdentityName:
    """Deprecated (deadname) identity name with suppressed visibility."""
    name = IdentityName(
        identity_id=sample_verified_profile.user_id,
        name_type=NameType.given,
        name_value={"en": "[REDACTED]"},
        is_primary=False,
        is_deprecated=True,
        visibility_level=VisibilityLevel.historical_suppressed,
    )
    db_session.add(name)
    db_session.commit()
    db_session.refresh(name)
    return name


@pytest.fixture
def sample_profiles_with_names(db_session: Session) -> list[BaseProfile]:
    """Three profiles: Western, Chinese, and Mononym naming conventions."""
    profiles = []

    profile1 = BaseProfile(
        account_type=AccountType.verified,
        legal_name="John Smith",
        primary_email="john.smith@example.com",
        preferred_language="en",
    )
    db_session.add(profile1)
    db_session.flush()

    name1 = IdentityName(
        identity_id=profile1.user_id,
        name_type=NameType.full_name,
        name_value={"en": "John Smith"},
        is_primary=True,
    )
    db_session.add(name1)
    profiles.append(profile1)

    profile2 = BaseProfile(
        account_type=AccountType.unverified,
        primary_email="li.ming@example.com",
        preferred_language="zh",
    )
    db_session.add(profile2)
    db_session.flush()

    name2 = IdentityName(
        identity_id=profile2.user_id,
        name_type=NameType.full_name,
        name_value={"zh": "李明", "en": "Li Ming"},
        is_primary=True,
    )
    db_session.add(name2)
    profiles.append(profile2)

    profile3 = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Sukarno",
        primary_email="sukarno@example.id",
        preferred_language="id",
    )
    db_session.add(profile3)
    db_session.flush()

    name3 = IdentityName(
        identity_id=profile3.user_id,
        name_type=NameType.full_name,
        name_value={"id": "Sukarno", "en": "Sukarno"},
        is_primary=True,
    )
    db_session.add(name3)
    profiles.append(profile3)

    db_session.commit()
    for profile in profiles:
        db_session.refresh(profile)

    return profiles


@pytest.fixture
def profile_repository(db_session: Session) -> ProfileRepository:
    return ProfileRepository(db_session)


@pytest.fixture
def profile_service(profile_repository: ProfileRepository) -> ProfileService:
    return ProfileService(profile_repository)


@pytest.fixture
def audit_repository(db_session: Session) -> AuditRepository:
    return AuditRepository(db_session)


@pytest.fixture
def audit_service(audit_repository: AuditRepository) -> AuditService:
    return AuditService(audit_repository)


@pytest.fixture
def sample_verified_auth_user(
    db_session: Session, sample_verified_profile: BaseProfile
) -> AuthUser:
    """Create an AuthUser with verified email for the sample verified profile."""
    auth_user = AuthUser(
        user_id=str(sample_verified_profile.user_id),
        email=sample_verified_profile.primary_email,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    db_session.refresh(auth_user)
    return auth_user


@pytest.fixture
def verified_token(sample_verified_auth_user: AuthUser) -> str:
    """JWT access token for the verified sample profile."""
    return create_access_token(
        user_id=str(sample_verified_auth_user.user_id),
        email=sample_verified_auth_user.email,
        account_type="verified",
    )


@pytest.fixture
def sample_pseudonymous_auth_user(
    db_session: Session, sample_pseudonymous_profile: BaseProfile
) -> AuthUser:
    """Create an AuthUser with verified email for the pseudonymous profile."""
    auth_user = AuthUser(
        user_id=str(sample_pseudonymous_profile.user_id),
        email=sample_pseudonymous_profile.primary_email,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    db_session.refresh(auth_user)
    return auth_user


@pytest.fixture
def pseudonymous_token(sample_pseudonymous_auth_user: AuthUser) -> str:
    """JWT access token for the pseudonymous sample profile."""
    return create_access_token(
        user_id=str(sample_pseudonymous_auth_user.user_id),
        email=sample_pseudonymous_auth_user.email,
        account_type="pseudonymous",
    )


@pytest.fixture
def unverified_email_auth_user(
    db_session: Session, sample_unverified_profile: BaseProfile
) -> AuthUser:
    """Create an AuthUser with unverified email for the unverified profile."""
    auth_user = AuthUser(
        user_id=str(sample_unverified_profile.user_id),
        email=sample_unverified_profile.primary_email,
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=False,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    db_session.refresh(auth_user)
    return auth_user


@pytest.fixture
def unverified_email_token(unverified_email_auth_user: AuthUser) -> str:
    """JWT access token for an unverified-email user."""
    return create_access_token(
        user_id=str(unverified_email_auth_user.user_id),
        email=unverified_email_auth_user.email,
        account_type="unverified",
    )
