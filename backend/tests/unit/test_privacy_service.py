"""Tests for GDPR Article 15 data export with mocked repositories."""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from src.services.privacy_service import (
    PrivacyService,
    ProfileNotFoundError,
    GDPR_METADATA,
)
from src.models.audit import AuditEventType, AuditOperation


@pytest.fixture
def mock_profile_repo():
    return Mock()


@pytest.fixture
def mock_context_repo():
    return Mock()


@pytest.fixture
def mock_auth_repo():
    return Mock()


@pytest.fixture
def mock_oauth_repo():
    return Mock()


@pytest.fixture
def mock_audit_service():
    return Mock()


@pytest.fixture
def privacy_service(
    mock_profile_repo,
    mock_context_repo,
    mock_auth_repo,
    mock_oauth_repo,
    mock_audit_service,
):
    return PrivacyService(
        profile_repo=mock_profile_repo,
        context_repo=mock_context_repo,
        auth_repo=mock_auth_repo,
        oauth_repo=mock_oauth_repo,
        audit_service=mock_audit_service,
    )


def _make_profile(user_id):
    """Create a mock BaseProfile."""
    profile = Mock()
    profile.user_id = user_id
    profile.account_type = Mock(value="verified")
    profile.legal_name = "Test User"
    profile.primary_email = "test@example.com"
    profile.primary_phone = "+1-555-0100"
    profile.preferred_language = "en"
    profile.valid_from = None
    profile.valid_to = None
    profile.created_at = None
    profile.updated_at = None
    return profile


def _make_identity_name(identity_id, name_type="full_name", deprecated=False):
    """Create a mock IdentityName."""
    name = Mock()
    name.id = uuid4()
    name.identity_id = identity_id
    name.name_type = Mock(value=name_type)
    name.name_value = {"en": "Test User"}
    name.is_primary = True
    name.is_deprecated = deprecated
    name.visibility_level = Mock(
        value="historical_suppressed" if deprecated else "public"
    )
    name.context_id = None
    name.valid_from = None
    name.valid_to = None
    name.created_at = None
    name.updated_at = None
    return name


def _make_context(user_id, context_type="professional", active=True):
    """Create a mock ContextProfile."""
    ctx = Mock()
    ctx.id = uuid4()
    ctx.user_id = user_id
    ctx.context_type = Mock(value=context_type)
    ctx.context_name = f"My {context_type}"
    ctx.display_name_override = None
    ctx.email_override = None
    ctx.phone_override = None
    ctx.bio = None
    ctx.is_active = active
    ctx.valid_from = None
    ctx.valid_to = None
    ctx.created_at = None
    ctx.updated_at = None
    return ctx


def _make_auth_user(user_id):
    """Create a mock AuthUser (no sensitive fields)."""
    auth = Mock()
    auth.email = "test@example.com"
    auth.is_email_verified = True
    auth.email_verified_at = None
    auth.last_login_at = None
    auth.password_changed_at = None
    auth.is_admin = False
    auth.created_at = None
    return auth


def _make_consent(user_id, client_id="app-1"):
    """Create a mock OAuthConsent."""
    consent = Mock()
    consent.id = uuid4()
    consent.client_id = client_id
    consent.user_id = user_id
    consent.granted_scopes = ["profile:read", "email"]
    consent.context_profile_id = None
    consent.consent_method = Mock(value="explicit")
    consent.granted_at = None
    consent.expires_at = None
    consent.withdrawn_at = None
    return consent


class TestExportUserData:
    """Tests for the export_user_data method."""

    def test_export_returns_all_sections(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export contains all expected top-level sections."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        assert "export_metadata" in result
        assert "profile" in result
        assert "identity_names" in result
        assert "context_profiles" in result
        assert "authentication" in result
        assert "oauth_consents" in result
        assert "gdpr_metadata" in result

    def test_export_metadata_format(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export metadata contains version, legal basis, and timestamp."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        meta = result["export_metadata"]
        assert meta["format_version"] == "1.0"
        assert "Article 15" in meta["legal_basis"]
        assert meta["user_id"] == user_id
        assert meta["exported_at"] is not None

    def test_export_profile_data(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Profile section contains expected fields."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        profile = result["profile"]
        assert profile["user_id"] == user_id
        assert profile["account_type"] == "verified"
        assert profile["primary_email"] == "test@example.com"
        assert profile["legal_name"] == "Test User"

    def test_export_includes_deprecated_names(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """GDPR requires all data including deprecated (dead) names."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        names = [
            _make_identity_name(user_id),
            _make_identity_name(user_id, deprecated=True),
        ]
        mock_profile_repo.get_identity_names.return_value = names
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        assert len(result["identity_names"]) == 2
        mock_profile_repo.get_identity_names.assert_called_once_with(
            user_id, include_deprecated=True
        )

    def test_export_includes_inactive_contexts(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export includes both active and inactive context profiles."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        contexts = [
            _make_context(user_id, active=True),
            _make_context(user_id, context_type="social", active=False),
        ]
        mock_context_repo.get_user_context_profiles.return_value = contexts
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        assert len(result["context_profiles"]) == 2
        mock_context_repo.get_user_context_profiles.assert_called_once_with(
            user_id, include_inactive=True
        )

    def test_export_excludes_sensitive_auth_fields(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Authentication export must not contain password hash or tokens."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        auth = _make_auth_user(user_id)
        auth.password_hash = "$argon2id$SENSITIVE_HASH"
        auth.verification_token = "secret-token"
        auth.reset_token = "secret-reset"
        mock_auth_repo.get_by_user_id.return_value = auth
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        auth_export = result["authentication"]
        assert "password_hash" not in auth_export
        assert "verification_token" not in auth_export
        assert "reset_token" not in auth_export
        assert auth_export["email"] == "test@example.com"

    def test_export_includes_oauth_consents(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export includes active and withdrawn consents."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        consents = [
            _make_consent(user_id, "app-1"),
            _make_consent(user_id, "app-2"),
        ]
        mock_oauth_repo.get_user_consents.return_value = consents

        result = privacy_service.export_user_data(user_id)

        assert len(result["oauth_consents"]) == 2
        assert result["oauth_consents"][0]["client_id"] == "app-1"
        assert result["oauth_consents"][0]["granted_scopes"] == ["profile:read", "email"]

    def test_export_includes_gdpr_metadata(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export contains static GDPR metadata block."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        gdpr = result["gdpr_metadata"]
        assert "processing_purposes" in gdpr
        assert "retention_periods" in gdpr
        assert "data_subject_rights" in gdpr
        assert "data_sources" in gdpr
        assert gdpr == GDPR_METADATA

    def test_export_raises_on_missing_profile(
        self, privacy_service, mock_profile_repo
    ):
        """ProfileNotFoundError raised when profile does not exist."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = None

        with pytest.raises(ProfileNotFoundError):
            privacy_service.export_user_data(user_id)

    def test_export_logs_audit_event(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo, mock_audit_service
    ):
        """Export triggers a privacy.data_export audit event."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        privacy_service.export_user_data(
            user_id=user_id,
            actor_id=user_id,
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
        )

        mock_audit_service.log_event.assert_called_once_with(
            event_type=AuditEventType.data_export,
            user_id=user_id,
            actor_id=user_id,
            resource_type="user_data",
            resource_id=str(user_id),
            operation=AuditOperation.create,
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
            legal_basis="gdpr_art_15_access",
        )

    def test_export_works_without_audit_service(
        self, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export succeeds when audit_service is None."""
        service = PrivacyService(
            profile_repo=mock_profile_repo,
            context_repo=mock_context_repo,
            auth_repo=mock_auth_repo,
            oauth_repo=mock_oauth_repo,
            audit_service=None,
        )
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = service.export_user_data(user_id)
        assert result["profile"]["user_id"] == user_id

    def test_export_handles_no_auth_user(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export handles case where auth_users record is missing."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = None
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        assert result["authentication"] is None

    def test_export_empty_collections(
        self, privacy_service, mock_profile_repo, mock_context_repo,
        mock_auth_repo, mock_oauth_repo
    ):
        """Export handles user with no names, contexts, or consents."""
        user_id = uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(user_id)
        mock_profile_repo.get_identity_names.return_value = []
        mock_context_repo.get_user_context_profiles.return_value = []
        mock_auth_repo.get_by_user_id.return_value = _make_auth_user(user_id)
        mock_oauth_repo.get_user_consents.return_value = []

        result = privacy_service.export_user_data(user_id)

        assert result["identity_names"] == []
        assert result["context_profiles"] == []
        assert result["oauth_consents"] == []
