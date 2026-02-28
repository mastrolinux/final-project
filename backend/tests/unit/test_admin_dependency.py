"""
Unit tests for admin authentication dependency.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.dependencies.auth import require_admin
from src.models.auth import AuthUser


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        user = MagicMock(spec=AuthUser)
        user.is_admin = True
        user.email = "admin@example.com"
        return user

    @pytest.fixture
    def mock_regular_user(self):
        """Create a mock regular (non-admin) user."""
        user = MagicMock(spec=AuthUser)
        user.is_admin = False
        user.email = "user@example.com"
        return user

    @pytest.fixture
    def mock_env_admin_user(self):
        """Create a mock user that is admin via env var."""
        user = MagicMock(spec=AuthUser)
        user.is_admin = False
        user.email = "env.admin@example.com"
        return user

    @pytest.mark.asyncio
    async def test_admin_by_db_flag(self, mock_admin_user):
        """Test that user with is_admin=True is allowed."""
        result = await require_admin(mock_admin_user)
        assert result == mock_admin_user

    @pytest.mark.asyncio
    async def test_admin_by_env_var(self, mock_env_admin_user):
        """Test that user in ADMIN_USER_EMAILS is allowed."""
        with patch("src.api.dependencies.auth.settings") as mock_settings:
            mock_settings.admin_emails = ["env.admin@example.com"]
            result = await require_admin(mock_env_admin_user)
            assert result == mock_env_admin_user

    @pytest.mark.asyncio
    async def test_non_admin_rejected(self, mock_regular_user):
        """Test that non-admin user is rejected with 403."""
        with patch("src.api.dependencies.auth.settings") as mock_settings:
            mock_settings.admin_emails = []
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(mock_regular_user)

            assert exc_info.value.status_code == 403
            assert "Admin access required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_email_case_insensitive(self, mock_env_admin_user):
        """Test that email matching is case-insensitive."""
        mock_env_admin_user.email = "ENV.ADMIN@EXAMPLE.COM"
        with patch("src.api.dependencies.auth.settings") as mock_settings:
            mock_settings.admin_emails = ["env.admin@example.com"]
            result = await require_admin(mock_env_admin_user)
            assert result == mock_env_admin_user

    @pytest.mark.asyncio
    async def test_db_flag_takes_precedence(self, mock_admin_user):
        """Test that DB flag is checked before env var."""
        # Even with empty admin_emails, db flag should work
        with patch("src.api.dependencies.auth.settings") as mock_settings:
            mock_settings.admin_emails = []
            result = await require_admin(mock_admin_user)
            assert result == mock_admin_user
