"""
Redis-based token blacklist for refresh token rotation.
"""

import logging
from typing import Optional

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from src.core.config import settings

logger = logging.getLogger(__name__)

# Default TTL for blacklisted tokens (30 days in seconds)
DEFAULT_BLACKLIST_TTL = 30 * 24 * 60 * 60  # 2592000 seconds


class TokenBlacklist:
    """Redis-backed JTI blacklist with fail-closed semantics and TTL-based cleanup."""

    _instance: Optional["TokenBlacklist"] = None
    _redis_client: redis.Redis | None = None

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection with connection pooling."""
        try:
            self._redis_client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._redis_client.ping()
            logger.info("Redis connection established for token blacklist")
        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}") from e

    def is_available(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            if self._redis_client is None:
                return False
            self._redis_client.ping()
            return True
        except (RedisConnectionError, RedisError):
            return False

    def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI is blacklisted (fail-closed on Redis error)."""
        if not jti:
            raise ValueError("JTI cannot be empty")

        try:
            key = f"blacklist:{jti}"
            if self._redis_client is None:
                raise RuntimeError("Redis client is not initialized")
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
        """Add a token JTI to the blacklist with automatic TTL expiration."""
        if not jti:
            raise ValueError("JTI cannot be empty")

        if ttl_seconds <= 0:
            raise ValueError("TTL must be positive")

        try:
            key = f"blacklist:{jti}"
            if self._redis_client is None:
                raise RuntimeError("Redis client is not initialized")
            self._redis_client.setex(key, ttl_seconds, "1")
            logger.info(f"Token {jti[:8]}... blacklisted for {ttl_seconds}s")

        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Redis error adding to blacklist: {e}")
            raise ConnectionError(
                "Failed to blacklist token. Authentication service degraded."
            ) from e

    def get_stats(self) -> dict:
        """Return blacklist statistics for health monitoring."""
        try:
            if self._redis_client is None:
                raise RuntimeError("Redis client is not initialized")
            cursor = 0
            count = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor, match="blacklist:*", count=100
                )
                count += len(keys)
                if cursor == 0:
                    break

            info = self._redis_client.info("memory")

            return {
                "blacklisted_tokens": count,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_connected": True,
            }

        except (RedisConnectionError, RedisError) as e:
            logger.error(f"Redis error getting stats: {e}")
            raise ConnectionError("Redis unavailable for stats") from e


_blacklist_instance: TokenBlacklist | None = None


def get_blacklist() -> TokenBlacklist:
    """Get the singleton TokenBlacklist instance."""
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
    """Reset the singleton instance (for testing)."""
    global _blacklist_instance

    if _blacklist_instance is not None:
        try:
            if _blacklist_instance._redis_client:
                _blacklist_instance._redis_client.close()
        except Exception:  # nosec: B110
            pass  # best-effort cleanup during teardown
        _blacklist_instance = None
