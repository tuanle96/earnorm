"""Cache manager implementation.

This module provides cache manager implementation that uses DI container.

Examples:
    ```python
    from earnorm.cache.core.manager import CacheManager
    from earnorm.di.container import Container

    # Create container and register components
    container = Container()
    container.register("redis_pool", lambda: RedisPool(...))

    # Create cache manager
    cache = CacheManager(
        container=container,
        backend_type="redis",
        prefix="app",
        ttl=300
    )

    # Use cache
    await cache.set("key", "value")
    value = await cache.get("key")
    await cache.delete("key")
    ```
"""

import logging
from typing import Any, Dict, List, Optional, Type

from earnorm.cache.backends.redis import RedisBackend
from earnorm.cache.core.backend import BaseCacheBackend
from earnorm.cache.core.exceptions import CacheError
from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.cache.serializers.json import JsonSerializer
from earnorm.di import Container

logger = logging.getLogger(__name__)


class CacheManager:
    """Cache manager implementation.

    This class provides high-level interface for cache operations.
    It uses DI container to get cache backend and serializer.

    Features:
    - Multiple backend support
    - Key prefixing
    - TTL support
    - Error handling
    - Batch operations

    Examples:
        ```python
        # Create cache manager
        cache = CacheManager(
            container=container,
            backend_type="redis",
            prefix="app",
            ttl=300
        )

        # Basic operations
        await cache.set("key", "value")
        value = await cache.get("key")
        await cache.delete("key")

        # Batch operations
        await cache.set_many({
            "key1": "value1",
            "key2": "value2"
        })
        values = await cache.get_many(["key1", "key2"])
        await cache.delete_many(["key1", "key2"])
        ```
    """

    def __init__(
        self,
        container: Container,
        backend_type: str = "redis",
        prefix: str = "app",
        ttl: int = 300,
    ) -> None:
        """Initialize cache manager.

        Args:
            container: DI container
            backend_type: Backend type (redis)
            prefix: Key prefix
            ttl: Default TTL in seconds

        Raises:
            CacheError: If backend type is not supported
        """
        if backend_type not in ["redis"]:
            raise CacheError(f"Unsupported backend type: {backend_type}")

        self._container = container
        self._backend_type = backend_type
        self._prefix = prefix
        self._ttl = ttl
        self._backend: Optional[BaseCacheBackend] = None

    @property
    def is_connected(self) -> bool:
        """Check if cache backend is connected.

        Returns:
            bool: True if backend is initialized and connected
        """
        try:
            return self._backend is not None
        except Exception:
            return False

    @property
    def backend(self) -> BaseCacheBackend:
        """Get cache backend.

        Returns:
            BaseCacheBackend: Cache backend

        Raises:
            CacheError: If backend is not initialized or initialization fails
        """
        if self._backend is None:
            try:
                # Get backend class
                backend_class = self._get_backend_class()

                # Get serializer
                serializer = self._get_serializer()

                # Create backend instance
                if self._backend_type == "redis":
                    self._backend = RedisBackend(
                        container=self._container,
                        serializer=serializer,
                        prefix=self._prefix,
                        ttl=self._ttl,
                    )
                else:
                    self._backend = backend_class(serializer=serializer)
            except Exception as e:
                raise CacheError("Failed to initialize backend") from e
        return self._backend

    def _get_backend_class(self) -> Type[BaseCacheBackend]:
        """Get backend class.

        Returns:
            Type[BaseCacheBackend]: Backend class

        Raises:
            CacheError: If backend type is not supported
        """
        if self._backend_type == "redis":
            return RedisBackend
        raise CacheError(f"Unsupported backend type: {self._backend_type}")

    def _get_serializer(self) -> SerializerProtocol:
        """Get serializer.

        Returns:
            SerializerProtocol: Value serializer

        Raises:
            CacheError: If failed to get serializer
        """
        try:
            return JsonSerializer()
        except Exception as e:
            raise CacheError("Failed to create serializer") from e

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[str]: Cached value or None if not found

        Raises:
            CacheError: If failed to get value
        """
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds

        Raises:
            CacheError: If failed to set value
        """
        await self.backend.set(key, value, ttl)

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key

        Raises:
            CacheError: If failed to delete value
        """
        await self.backend.delete(key)

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict[str, Any]: Dictionary of key-value pairs

        Raises:
            CacheError: If failed to get values
        """
        return await self.backend.get_many(keys)

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set multiple values in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Optional TTL in seconds

        Raises:
            CacheError: If failed to set values
        """
        await self.backend.set_many(mapping, ttl)

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple values from cache.

        Args:
            keys: List of cache keys

        Raises:
            CacheError: If failed to delete values
        """
        await self.backend.delete_many(keys)
