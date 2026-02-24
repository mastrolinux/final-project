"""Integration tests for privacy data export endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.core.security import create_access_token
from src.models.auth import AuthUser
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel
from src.models.context import ContextProfile, ContextType


class TestPrivacyExportEndpoint:
    """Test GET /api/v1/privacy/export endpoint."""

    @pytest.fixture
    def client(self, db_session: Session):
        """Test client with database override."""
        def override_get_db():
            try:
                yield db_session
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def user_profile(self, db_session: Session):
        """Create a user with profile, auth, names, and context."""
        profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000060",
            account_type=AccountType.verified,
            legal_name="Export Test User",
            primary_email="export.user@example.com",
            primary_phone="+1-555-0160",
            preferred_language="en",
        )
        db_session.add(profile)
        db_session.commit()

        auth_user = AuthUser(
            user_id="00000000-0000-0000-0000-000000000060",
            email="export.user@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False,
        )
        db_session.add(auth_user)
        db_session.commit()

        name = IdentityName(
            identity_id=profile.user_id,
            name_type=NameType.full_name,
            name_value={"en": "Export Test User", "es": "Usuario de Prueba"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public,
        )
        db_session.add(name)

        deprecated_name = IdentityName(
            identity_id=profile.user_id,
            name_type=NameType.given,
            name_value={"en": "[Previous Name]"},
            is_primary=False,
            is_deprecated=True,
            visibility_level=VisibilityLevel.historical_suppressed,
        )
        db_session.add(deprecated_name)
        db_session.commit()

        context = ContextProfile(
            user_id=profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            display_name_override="Dr. Export User",
            email_override="export@work.com",
            is_active=True,
        )
        db_session.add(context)
        db_session.commit()

        return auth_user

    @pytest.fixture
    def user_token(self, user_profile):
        """JWT token for the test user."""
        return create_access_token(
            user_id=str(user_profile.user_id),
            email=user_profile.email,
            account_type="verified",
        )

    def test_export_requires_authentication(self, client):
        """GET /privacy/export returns 401 without token."""
        response = client.get("/api/v1/privacy/export")
        assert response.status_code == 401

    def test_export_returns_200(self, client, user_token, user_profile):
        """Authenticated request returns 200 with export data."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200

    def test_export_response_structure(self, client, user_token, user_profile):
        """Response contains all required top-level keys."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        data = response.json()

        assert "export_metadata" in data
        assert "profile" in data
        assert "identity_names" in data
        assert "context_profiles" in data
        assert "authentication" in data
        assert "oauth_consents" in data
        assert "gdpr_metadata" in data

    def test_export_metadata_fields(self, client, user_token, user_profile):
        """Export metadata includes version, legal basis, and timestamp."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        meta = response.json()["export_metadata"]

        assert meta["format_version"] == "1.0"
        assert "Article 15" in meta["legal_basis"]
        assert meta["user_id"] == "00000000-0000-0000-0000-000000000060"
        assert meta["exported_at"] is not None

    def test_export_profile_data(self, client, user_token, user_profile):
        """Profile section contains correct user data."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        profile = response.json()["profile"]

        assert profile["primary_email"] == "export.user@example.com"
        assert profile["legal_name"] == "Export Test User"
        assert profile["account_type"] == "verified"
        assert profile["preferred_language"] == "en"

    def test_export_includes_all_names(self, client, user_token, user_profile):
        """Export includes both active and deprecated identity names."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        names = response.json()["identity_names"]

        assert len(names) == 2
        types = [n["name_type"] for n in names]
        assert "full_name" in types
        assert "given" in types

        deprecated = [n for n in names if n["is_deprecated"]]
        assert len(deprecated) == 1
        assert deprecated[0]["visibility_level"] == "historical_suppressed"

    def test_export_includes_multilingual_names(
        self, client, user_token, user_profile
    ):
        """Name values preserve multilingual JSONB structure."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        names = response.json()["identity_names"]
        full_name = next(n for n in names if n["name_type"] == "full_name")

        assert full_name["name_value"]["en"] == "Export Test User"
        assert full_name["name_value"]["es"] == "Usuario de Prueba"

    def test_export_includes_context_profiles(
        self, client, user_token, user_profile
    ):
        """Export includes context profiles with override fields."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        contexts = response.json()["context_profiles"]

        assert len(contexts) == 1
        assert contexts[0]["context_type"] == "professional"
        assert contexts[0]["context_name"] == "Work"
        assert contexts[0]["display_name_override"] == "Dr. Export User"
        assert contexts[0]["email_override"] == "export@work.com"

    def test_export_auth_excludes_sensitive_fields(
        self, client, user_token, user_profile
    ):
        """Authentication section excludes password hash and tokens."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        auth = response.json()["authentication"]

        assert "password_hash" not in auth
        assert "verification_token" not in auth
        assert "reset_token" not in auth
        assert auth["email"] == "export.user@example.com"
        assert auth["is_email_verified"] is True

    def test_export_gdpr_metadata_present(
        self, client, user_token, user_profile
    ):
        """GDPR metadata contains required informational sections."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        gdpr = response.json()["gdpr_metadata"]

        assert len(gdpr["processing_purposes"]) > 0
        assert "retention_periods" in gdpr
        assert len(gdpr["data_subject_rights"]) > 0
        assert len(gdpr["data_sources"]) > 0
        assert "recipients_or_categories" in gdpr
        assert "automated_decision_making" in gdpr

    def test_export_empty_consents(self, client, user_token, user_profile):
        """User with no OAuth consents gets empty array."""
        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.json()["oauth_consents"] == []

    def test_export_returns_only_own_data(
        self, client, user_token, user_profile, db_session
    ):
        """Authenticated user receives only their own data, not other users'."""
        other_profile = BaseProfile(
            user_id="00000000-0000-0000-0000-000000000061",
            account_type=AccountType.verified,
            legal_name="Other User",
            primary_email="other@example.com",
            preferred_language="en",
        )
        db_session.add(other_profile)
        db_session.commit()

        other_auth = AuthUser(
            user_id="00000000-0000-0000-0000-000000000061",
            email="other@example.com",
            password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
            is_email_verified=True,
            is_admin=False,
        )
        db_session.add(other_auth)

        other_name = IdentityName(
            identity_id=other_profile.user_id,
            name_type=NameType.full_name,
            name_value={"en": "Other User"},
            is_primary=True,
        )
        db_session.add(other_name)
        db_session.commit()

        response = client.get(
            "/api/v1/privacy/export",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        data = response.json()

        assert data["profile"]["user_id"] == "00000000-0000-0000-0000-000000000060"
        assert data["profile"]["primary_email"] == "export.user@example.com"
        for name in data["identity_names"]:
            assert "Other User" not in str(name["name_value"])
