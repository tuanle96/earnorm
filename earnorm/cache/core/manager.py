"""Cache manager implementation.

This module provides the main cache manager class that coordinates all
cache operations. It handles:
- Backend management
- Value serialization
- Error handling
- Metrics collection
- Health checks

Examples:
    ```python
    from earnorm.cache import CacheManager
    from earnorm.cache.backends.redis import RedisBackend
    from earnorm.pool.factory import PoolFactory

    # Create Redis pool
    redis_pool = await PoolFactory.create_redis_pool(
        host="localhost",
        port=6379,
        db=0,
        min_size=5,
        max_size=20
    )

    # Create Redis backend with pool
    redis_backend = RedisBackend(pool=redis_pool)

    # Initialize cache manager
    cache = CacheManager(
        backend=redis_backend,
        default_ttl=3600,
        enabled=True
    )
    await cache.init()

    # Basic operations
    await cache.set("key", {"name": "value"}, ttl=300)
    value = await cache.get("key")

    # Batch operations
    await cache.set_many({
        "key1": "value1",
        "key2": "value2"
    }, ttl=300)
    values = await cache.get_many(["key1", "key2"])

    # Pattern operations
    keys = await cache.scan("user:*")
    await cache.delete(*keys)

    # Health check
    if cache.is_connected:
        info = await cache.info()
        print(f"Cache stats: {info}")
    ```
"""

import logging
from typing import Any, Dict, List, Optional

from earnorm.cache.backends.base import CacheBackend
from earnorm.cache.core.exceptions import CacheError, ConnectionError
from earnorm.di.lifecycle import LifecycleAware

logger = logging.getLogger(__name__)


class CacheManager(LifecycleAware):
    """Cache manager.

    This class provides a high-level interface for cache operations.
    It handles backend management, serialization, error handling,
    and metrics collection.

    Features:
    - Backend abstraction (Redis, etc.)
    - JSON serialization
    - TTL management
    - Error handling and logging
    - Metrics collection
    - Health checks
    - Distributed locking

    Examples:
        ```python
        from earnorm.pool.factory import PoolFactory
        from earnorm.cache.backends.redis import RedisBackend
        from earnorm.cache import CacheManager

        # Create Redis pool
        redis_pool = await PoolFactory.create_redis_pool(
            host="localhost",
            port=6379,
            db=0,
            min_size=5,
            max_size=20
        )

        # Create Redis backend with pool
        redis_backend = RedisBackend(pool=redis_pool)

        # Initialize cache manager
        cache = CacheManager(
            backend=redis_backend,
            default_ttl=3600,
            enabled=True
        )
        await cache.init()

        # Basic operations
        await cache.set("key", "value")
        value = await cache.get("key")
        ```
    """

    def __init__(
        self,
        backend: CacheBackend,
        default_ttl: int = 3600,
        enabled: bool = True,
    ) -> None:
        """Initialize cache manager.

        Args:
            backend: Cache backend implementation
            default_ttl: Default TTL in seconds
            enabled: Whether cache is enabled
        """
        self._backend = backend
        self._default_ttl = default_ttl
        self._enabled = enabled

    async def init(self) -> None:
        """Initialize cache manager."""
        if not self._enabled:
            return

        if not self._backend:
            raise CacheError("No cache backend provided")

        if not self._backend.is_connected:
            raise ConnectionError("Cache backend is not connected")

        logger.info("Cache manager initialized")

    async def destroy(self) -> None:
        """Destroy cache manager."""
        if not self._enabled:
            return

        if self._backend:
            try:
                await self._backend.clear()
                logger.info("Cache manager destroyed")
            except Exception as e:
                logger.error("Failed to destroy cache manager: %s", e)

    @property
    def id(self) -> Optional[str]:
        """Get manager ID."""
        return "cache_manager"

    @property
    def data(self) -> Dict[str, str]:
        """Get manager data."""
        return {
            "enabled": str(self._enabled).lower(),
            "default_ttl": str(self._default_ttl),
            "backend": self._backend.__class__.__name__ if self._backend else "none",
            "connected": str(
                self._backend.is_connected if self._backend else False
            ).lower(),
        }

    @property
    def is_connected(self) -> bool:
        """Check if cache is connected.

        Returns:
            bool: True if cache is connected, False otherwise
        """
        return self._enabled and bool(self._backend) and self._backend.is_connected

    async def get(self, key: str) -> Any:
        """Get value by key.

        Args:
            key: Cache key

        Returns:
            Any: Cached value or None if not found

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return None

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.get(key)
        except Exception as e:
            logger.error("Failed to get cache key %s: %s", key, e)
            raise CacheError(f"Failed to get cache key {key}") from e

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value by key.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: None)

        Returns:
            bool: True if value was set, False otherwise

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return False

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.set(key, value, ttl or self._default_ttl)
        except Exception as e:
            logger.error("Failed to set cache key %s: %s", key, e)
            raise CacheError(f"Failed to set cache key {key}") from e

    async def delete(self, *keys: str) -> int:
        """Delete keys.

        Args:
            *keys: Cache keys to delete

        Returns:
            int: Number of keys deleted

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return 0

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.delete(*keys)
        except Exception as e:
            logger.error("Failed to delete cache keys %s: %s", keys, e)
            raise CacheError(f"Failed to delete cache keys {keys}") from e

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key

        Returns:
            bool: True if key exists, False otherwise

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return False

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.exists(key)
        except Exception as e:
            logger.error("Failed to check cache key %s: %s", key, e)
            raise CacheError(f"Failed to check cache key {key}") from e

    async def clear(self) -> bool:
        """Clear all keys.

        Returns:
            bool: True if all keys were cleared, False otherwise

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return False

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.clear()
        except Exception as e:
            logger.error("Failed to clear cache: %s", e)
            raise CacheError("Failed to clear cache") from e

    async def scan(self, pattern: str) -> List[str]:
        """Scan keys by pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            List[str]: List of matching keys

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return []

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.scan(pattern)
        except Exception as e:
            logger.error("Failed to scan cache keys %s: %s", pattern, e)
            raise CacheError(f"Failed to scan cache keys {pattern}") from e

    async def info(self) -> Dict[str, str]:
        """Get cache info.

        Returns:
            Dict[str, str]: Cache information

        Raises:
            CacheError: If cache is disabled or backend error occurs
            ConnectionError: If cache is not connected
        """
        if not self._enabled:
            return {"enabled": "false", "connected": "false"}

        if not self.is_connected:
            raise ConnectionError("Cache is not connected")

        try:
            return await self._backend.info()
        except Exception as e:
            logger.error("Failed to get cache info: %s", e)
            raise CacheError("Failed to get cache info") from e
