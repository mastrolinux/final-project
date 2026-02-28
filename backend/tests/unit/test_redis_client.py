"""Tests for token blacklist operations with mocked Redis."""

from unittest.mock import Mock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError


class TestTokenBlacklist:
    """Test TokenBlacklist Redis operations."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock = Mock()
        mock.ping.return_value = True
        mock.exists.return_value = 0
        mock.setex.return_value = True
        mock.scan.return_value = (0, [])
        mock.info.return_value = {"used_memory_human": "1M"}
        return mock

    @pytest.fixture
    def blacklist_with_mock(self, mock_redis_client):
        """Create TokenBlacklist with mocked Redis."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.return_value = mock_redis_client
            from src.core.redis_client import TokenBlacklist

            blacklist = TokenBlacklist("redis://localhost:6379/0")
            return blacklist, mock_redis_client

    def test_init_connects_to_redis(self, mock_redis_client):
        """Test TokenBlacklist establishes Redis connection on init."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_from_url.return_value = mock_redis_client

            from src.core.redis_client import TokenBlacklist

            blacklist = TokenBlacklist("redis://localhost:6379/0")

            mock_from_url.assert_called_once()
            mock_redis_client.ping.assert_called_once()

    def test_init_raises_on_connection_failure(self):
        """Test TokenBlacklist raises ConnectionError if Redis unavailable."""
        with patch("src.core.redis_client.redis.from_url") as mock_from_url:
            mock_redis = Mock()
            mock_redis.ping.side_effect = RedisConnectionError("Connection refused")
            mock_from_url.return_value = mock_redis

            from src.core.redis_client import TokenBlacklist

            with pytest.raises(ConnectionError) as exc_info:
                TokenBlacklist("redis://localhost:6379/0")

            assert "Redis connection failed" in str(exc_info.value)

    def test_is_available_returns_true_when_connected(self, blacklist_with_mock):
        """Test is_available returns True when Redis is responding."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.ping.return_value = True

        assert blacklist.is_available() is True

    def test_is_available_returns_false_on_error(self, blacklist_with_mock):
        """Test is_available returns False on Redis error."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.ping.side_effect = RedisConnectionError("Connection lost")

        assert blacklist.is_available() is False

    def test_is_blacklisted_returns_false_when_not_exists(self, blacklist_with_mock):
        """Test is_blacklisted returns False when JTI not in Redis."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.exists.return_value = 0

        result = blacklist.is_blacklisted("test-jti-123")

        assert result is False
        mock_redis.exists.assert_called_once_with("blacklist:test-jti-123")

    def test_is_blacklisted_returns_true_when_exists(self, blacklist_with_mock):
        """Test is_blacklisted returns True when JTI in Redis."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.exists.return_value = 1

        result = blacklist.is_blacklisted("revoked-jti-456")

        assert result is True
        mock_redis.exists.assert_called_once_with("blacklist:revoked-jti-456")

    def test_is_blacklisted_raises_on_redis_error(self, blacklist_with_mock):
        """Test is_blacklisted raises ConnectionError on Redis failure."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.exists.side_effect = RedisConnectionError("Connection lost")

        with pytest.raises(ConnectionError) as exc_info:
            blacklist.is_blacklisted("test-jti")

        assert "blacklist unavailable" in str(exc_info.value)

    def test_is_blacklisted_raises_on_empty_jti(self, blacklist_with_mock):
        """Test is_blacklisted raises ValueError for empty JTI."""
        blacklist, _ = blacklist_with_mock

        with pytest.raises(ValueError) as exc_info:
            blacklist.is_blacklisted("")

        assert "cannot be empty" in str(exc_info.value)

    def test_blacklist_token_sets_with_ttl(self, blacklist_with_mock):
        """Test blacklist_token sets key with correct TTL."""
        blacklist, mock_redis = blacklist_with_mock
        jti = "token-to-blacklist"
        ttl = 86400  # 1 day

        blacklist.blacklist_token(jti, ttl)

        mock_redis.setex.assert_called_once_with(f"blacklist:{jti}", ttl, "1")

    def test_blacklist_token_uses_default_ttl(self, blacklist_with_mock):
        """Test blacklist_token uses 30-day default TTL."""
        blacklist, mock_redis = blacklist_with_mock
        jti = "token-to-blacklist"

        blacklist.blacklist_token(jti)

        # Default TTL is 30 days = 2592000 seconds
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 30 * 24 * 60 * 60

    def test_blacklist_token_raises_on_redis_error(self, blacklist_with_mock):
        """Test blacklist_token raises ConnectionError on Redis failure."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.setex.side_effect = RedisConnectionError("Connection lost")

        with pytest.raises(ConnectionError) as exc_info:
            blacklist.blacklist_token("test-jti", 3600)

        assert "Failed to blacklist" in str(exc_info.value)

    def test_blacklist_token_raises_on_empty_jti(self, blacklist_with_mock):
        """Test blacklist_token raises ValueError for empty JTI."""
        blacklist, _ = blacklist_with_mock

        with pytest.raises(ValueError) as exc_info:
            blacklist.blacklist_token("", 3600)

        assert "cannot be empty" in str(exc_info.value)

    def test_blacklist_token_raises_on_invalid_ttl(self, blacklist_with_mock):
        """Test blacklist_token raises ValueError for non-positive TTL."""
        blacklist, _ = blacklist_with_mock

        with pytest.raises(ValueError) as exc_info:
            blacklist.blacklist_token("test-jti", 0)

        assert "TTL must be positive" in str(exc_info.value)

        with pytest.raises(ValueError):
            blacklist.blacklist_token("test-jti", -100)

    def test_get_stats_returns_statistics(self, blacklist_with_mock):
        """Test get_stats returns blacklist statistics."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.scan.return_value = (0, ["blacklist:jti1", "blacklist:jti2"])
        mock_redis.info.return_value = {"used_memory_human": "2.5M"}

        stats = blacklist.get_stats()

        assert stats["blacklisted_tokens"] == 2
        assert stats["redis_memory_used"] == "2.5M"
        assert stats["redis_connected"] is True

    def test_get_stats_raises_on_redis_error(self, blacklist_with_mock):
        """Test get_stats raises ConnectionError on Redis failure."""
        blacklist, mock_redis = blacklist_with_mock
        mock_redis.scan.side_effect = RedisConnectionError("Connection lost")

        with pytest.raises(ConnectionError) as exc_info:
            blacklist.get_stats()

        assert "Redis unavailable" in str(exc_info.value)


class TestGetBlacklistSingleton:
    """Test get_blacklist singleton function."""

    def test_get_blacklist_raises_when_disabled(self):
        """Test get_blacklist raises RuntimeError when Redis disabled."""
        with patch("src.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_ENABLED = False

            import src.core.redis_client as redis_module

            redis_module._blacklist_instance = None

            with pytest.raises(RuntimeError) as exc_info:
                from src.core.redis_client import get_blacklist

                get_blacklist()

            assert "Redis is disabled" in str(exc_info.value)

    def test_get_blacklist_returns_singleton(self):
        """Test get_blacklist returns same instance on multiple calls."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True

        with (
            patch("src.core.redis_client.settings") as mock_settings,
            patch("src.core.redis_client.redis.from_url") as mock_from_url,
        ):
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_from_url.return_value = mock_redis

            import src.core.redis_client as redis_module

            redis_module._blacklist_instance = None

            from src.core.redis_client import get_blacklist

            instance1 = get_blacklist()
            instance2 = get_blacklist()

            assert instance1 is instance2


class TestResetBlacklist:
    """Test reset_blacklist function for testing."""

    def test_reset_blacklist_clears_singleton(self):
        """Test reset_blacklist clears the singleton instance."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True

        with (
            patch("src.core.redis_client.settings") as mock_settings,
            patch("src.core.redis_client.redis.from_url") as mock_from_url,
        ):
            mock_settings.REDIS_ENABLED = True
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_from_url.return_value = mock_redis

            import src.core.redis_client as redis_module

            redis_module._blacklist_instance = None

            from src.core.redis_client import get_blacklist, reset_blacklist

            instance1 = get_blacklist()
            reset_blacklist()
            instance2 = get_blacklist()

            assert instance1 is not instance2
