"""
Redis Client Module

Provides Redis connection management and token blacklist operations
for refresh token rotation security.
"""

import logging
from typing import Optional

import redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError

from src.core.config import settings

logger = logging.getLogger(__name__)

# Default TTL for blacklisted tokens (30 days in seconds)
DEFAULT_BLACKLIST_TTL = 30 * 24 * 60 * 60  # 2592000 seconds


class TokenBlacklist:
    """
    Redis-based token blacklist for refresh token rotation.

    Stores revoked token JTIs (JWT IDs) in Redis with automatic expiration.
    Implements fail-closed behavior: if Redis is unavailable, operations
    raise exceptions to prevent token validation without blacklist checks.

    Key format: blacklist:{jti}
    Value: "1" (presence indicates blacklisted)
    TTL: Matches refresh token expiry (30 days by default)

    Security Model:
        - Fail closed: Redis unavailability causes 503 errors
        - Old tokens blacklisted BEFORE new tokens issued
        - TTL-based automatic cleanup eliminates maintenance jobs
    """

    _instance: Optional["TokenBlacklist"] = None
    _redis_client: Optional[redis.Redis] = None

    def __init__(self, redis_url: str):
        """
        Initialize Redis connection for token blacklist.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)

        Raises:
            ConnectionError: If initial Redis connection fails
        """
        self._redis_url = redis_url
        self._connect()

    def _connect(self) -> None:
        """
        Establish Redis connection with connection pooling.

        Raises:
            ConnectionError: If Redis connection cannot be established
        """
        try:
            self._redis_client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self._redis_client.ping()
            logger.info("Redis connection established for token blacklist")
        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}") from e

    def is_available(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is reachable and responding, False otherwise
        """
        try:
            if self._redis_client is None:
                return False
            self._redis_client.ping()
            return True
        except (RedisConnectionError, RedisError):
            return False

    def is_blacklisted(self, jti: str) -> bool:
        """
        Check if a token JTI is in the blacklist.

        Args:
            jti: JWT ID (unique token identifier)

        Returns:
            True if token is blacklisted (revoked), False otherwise

        Raises:
            ConnectionError: If Redis is unavailable (fail closed)
        """
        if not jti:
            raise ValueError("JTI cannot be empty")

        try:
            key = f"blacklist:{jti}"
            result = self._redis_client.exists(key)

            if result:
                logger.debug(f"Token {jti[:8]}... found in blacklist")

            return bool(result)

        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Redis error checking blacklist: {e}")
            raise ConnectionError(
                "Token blacklist unavailable. Authentication service degraded."
            ) from e

    def blacklist_token(self, jti: str, ttl_seconds: int = DEFAULT_BLACKLIST_TTL) -> None:
        """
        Add a token JTI to the blacklist with automatic expiration.

        The token remains blacklisted until TTL expires, after which Redis
        automatically removes the key. This eliminates the need for cleanup jobs.

        Args:
            jti: JWT ID (unique token identifier)
            ttl_seconds: Time-to-live in seconds (default: 30 days)

        Raises:
            ValueError: If jti is empty or ttl_seconds is invalid
            ConnectionError: If Redis is unavailable (fail closed)
        """
        if not jti:
            raise ValueError("JTI cannot be empty")

        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")

        try:
            key = f"blacklist:{jti}"
            self._redis_client.setex(key, ttl_seconds, "1")
            logger.info(f"Token {jti[:8]}... blacklisted for {ttl_seconds}s")

        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Redis error adding to blacklist: {e}")
            raise ConnectionError(
                "Failed to blacklist token. Authentication service degraded."
            ) from e

    def get_stats(self) -> dict:
        """
        Return blacklist statistics for health monitoring.

        Returns:
            Dictionary with blacklist statistics

        Raises:
            ConnectionError: If Redis is unavailable
        """
        try:
            # Count blacklist keys (approximate for large datasets)
            cursor = 0
            count = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor,
                    match="blacklist:*",
                    count=100
                )
                count += len(keys)
                if cursor == 0:
                    break

            info = self._redis_client.info("memory")

            return {
                "blacklisted_tokens": count,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_connected": True
            }

        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Redis error getting stats: {e}")
            raise ConnectionError("Redis unavailable for stats") from e


# Module-level singleton instance
_blacklist_instance: Optional[TokenBlacklist] = None


def get_blacklist() -> TokenBlacklist:
    """
    Get the singleton TokenBlacklist instance.

    Creates the instance on first call if Redis is enabled.

    Returns:
        TokenBlacklist singleton instance

    Raises:
        ConnectionError: If Redis is unavailable
        RuntimeError: If Redis is disabled in configuration
    """
    global _blacklist_instance

    if not settings.REDIS_ENABLED:
        raise RuntimeError(
            "Redis is disabled in configuration. "
            "Token refresh requires Redis for blacklist functionality."
        )

    if _blacklist_instance is None:
        _blacklist_instance = TokenBlacklist(settings.REDIS_URL)

    return _blacklist_instance


def reset_blacklist() -> None:
    """
    Reset the singleton instance (primarily for testing).

    Closes existing connection and clears the singleton.
    """
    global _blacklist_instance

    if _blacklist_instance is not None:
        try:
            if _blacklist_instance._redis_client:
                _blacklist_instance._redis_client.close()
        except Exception:
            pass
        _blacklist_instance = None
