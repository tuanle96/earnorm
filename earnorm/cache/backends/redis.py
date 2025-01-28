"""Redis cache backend implementation.

This module provides Redis cache backend implementation that uses Redis pool from DI container.

Examples:
    ```python
    from earnorm.cache.backends.redis import RedisBackend
    from earnorm.cache.serializers.json import JsonSerializer

    # Create backend
    backend = RedisBackend(
        serializer=JsonSerializer(),
        prefix="app",
        ttl=300
    )

    # Use backend
    await backend.set("key", "value")
    value = await backend.get("key")
    ```
"""

import logging
from typing import (
    Any,
    AsyncContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    cast,
)

# pylint: disable=no-name-in-module,import-error,import-self
from redis.asyncio import Redis

from earnorm.cache.core.backend import BaseCacheBackend
from earnorm.cache.core.exceptions import CacheError
from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.di import container

logger = logging.getLogger(__name__)

# Define type variables
RedisConn = TypeVar("RedisConn", bound=Redis, covariant=True)


# Define Pool Protocol
class AsyncPoolProtocol(Protocol[RedisConn]):
    async def connection(self) -> AsyncContextManager[RedisConn]: ...


class RedisBackend(BaseCacheBackend):
    """Redis cache backend implementation."""

    def __init__(
        self,
        serializer: SerializerProtocol,
        prefix: str = "app",
        ttl: int = 300,
    ) -> None:
        """Initialize Redis cache backend.

        Args:
            serializer: Value serializer
            prefix: Key prefix
            ttl: Default TTL in seconds
        """
        super().__init__(serializer=serializer)
        self._prefix = prefix
        self._ttl = ttl
        self._pool: Optional[AsyncPoolProtocol[Redis]] = None

    @property
    def pool(self) -> AsyncPoolProtocol[Redis]:
        """Get Redis pool.

        Returns:
            RedisPool: Redis connection pool

        Raises:
            CacheError: If pool is not initialized or cannot be retrieved
        """
        if self._pool is None:
            try:
                self._pool = cast(AsyncPoolProtocol[Redis], container.get("redis_pool"))
            except Exception as e:
                raise CacheError("Failed to get Redis pool") from e
        return self._pool

    def _prefix_key(self, key: str) -> str:
        """Add prefix to key.

        Args:
            key: Cache key

        Returns:
            str: Prefixed key
        """
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[str]: Cached value or None if not found

        Raises:
            CacheError: If failed to get value
        """
        try:
            async with await self.pool.connection() as conn:
                value = await conn.get(self._prefix_key(key))
                if value is None:
                    return None
                return self._serializer.loads(value.decode())
        except Exception as e:
            raise CacheError(f"Failed to get value for key {key}") from e

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds

        Raises:
            CacheError: If failed to set value
        """
        try:
            async with await self.pool.connection() as conn:
                await conn.set(
                    self._prefix_key(key),
                    self._serializer.dumps(value),
                    ex=ttl or self._ttl,
                )
        except Exception as e:
            raise CacheError(f"Failed to set value for key {key}") from e

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key

        Raises:
            CacheError: If failed to delete value
        """
        try:
            async with await self.pool.connection() as conn:
                await conn.delete(self._prefix_key(key))
        except Exception as e:
            raise CacheError(f"Failed to delete value for key {key}") from e

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict[str, Any]: Dictionary of key-value pairs

        Raises:
            CacheError: If failed to get values
        """
        if not keys:
            return {}

        try:
            async with await self.pool.connection() as conn:
                # Get values in pipeline
                pipeline = conn.pipeline()
                prefixed_keys = [self._prefix_key(key) for key in keys]
                for key in prefixed_keys:
                    pipeline.get(key)
                values: Sequence[Optional[bytes]] = await pipeline.execute()

                # Build result dictionary
                result: Dict[str, Any] = {}
                for key, value in zip(keys, values):
                    if value is not None:
                        result[key] = self._serializer.loads(value.decode())
                return result
        except Exception as e:
            raise CacheError("Failed to get multiple values") from e

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
        if not mapping:
            return

        try:
            async with await self.pool.connection() as conn:
                # Set values in pipeline
                pipeline = conn.pipeline()
                for key, value in mapping.items():
                    pipeline.set(
                        self._prefix_key(key),
                        self._serializer.dumps(value),
                        ex=ttl or self._ttl,
                    )
                await pipeline.execute()
        except Exception as e:
            raise CacheError("Failed to set multiple values") from e

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple values from cache.

        Args:
            keys: List of cache keys

        Raises:
            CacheError: If failed to delete values
        """
        if not keys:
            return

        try:
            async with await self.pool.connection() as conn:
                # Delete values in pipeline
                pipeline = conn.pipeline()
                for key in keys:
                    pipeline.delete(self._prefix_key(key))
                await pipeline.execute()
        except Exception as e:
            raise CacheError("Failed to delete multiple values") from e
