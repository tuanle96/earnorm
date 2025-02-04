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
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline

from earnorm.cache.core.backend import BaseCacheBackend
from earnorm.cache.core.exceptions import CacheError
from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.protocols.pool import AsyncPoolProtocol

logger = logging.getLogger(__name__)

# Define type variables
RedisConn = TypeVar("RedisConn", bound=Redis)
RedisValue = Union[str, bytes, int, float, None]
RedisPipelineResult = List[RedisValue]


class RedisConnectionManager:
    """Redis connection context manager."""

    def __init__(self, pool: AsyncPoolProtocol[Redis, None]) -> None:
        """Initialize Redis connection manager.

        Args:
            pool: Redis connection pool
        """
        self._pool = pool
        self._stack = AsyncExitStack()
        self._conn: Optional[RedisConnection[Redis]] = None

    async def __aenter__(self) -> RedisConnection[Redis]:
        """Enter async context.

        Returns:
            RedisConnection: Redis connection
        """
        conn_ctx = await self._pool.connection()
        redis_conn = await self._stack.enter_async_context(conn_ctx)
        self._conn = cast(RedisConnection[Redis], redis_conn)
        return self._conn

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit async context."""
        await self._stack.aclose()


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
        self._pool: Optional[AsyncPoolProtocol[Redis, None]] = None

    async def _init_pool(self) -> None:
        """Initialize Redis pool from container.

        Raises:
            CacheError: If pool initialization fails
        """
        if self._pool is None:
            try:
                from earnorm.di import container

                pool = await container.get("redis_pool")
                if not isinstance(pool, AsyncPoolProtocol):
                    raise CacheError("Invalid Redis pool type")
                self._pool = pool
            except Exception as e:
                raise CacheError("Failed to get Redis pool") from e

    async def get_pool(self) -> AsyncPoolProtocol[Redis, None]:
        """Get Redis pool.

        Returns:
            RedisPool: Redis connection pool

        Raises:
            CacheError: If pool is not initialized or cannot be retrieved
        """
        await self._init_pool()
        if self._pool is None:
            raise CacheError("Redis pool is not initialized")
        return self._pool

    def _prefix_key(self, key: str) -> str:
        """Add prefix to key.

        Args:
            key: Cache key

        Returns:
            str: Prefixed key
        """
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value or None if not found

        Raises:
            CacheError: If failed to get value
        """
        try:
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                value = await conn.execute_typed("get", self._prefix_key(key))
                value = cast(RedisValue, value)
                if value is None:
                    return None
                if isinstance(value, bytes):
                    return self._serializer.loads(value.decode())
                return None
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
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                await conn.execute_typed(
                    "set",
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
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                await conn.execute_typed("del", self._prefix_key(key))
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
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                # Get values using pipeline
                pipe: Pipeline = conn.pipeline()
                prefixed_keys = [self._prefix_key(key) for key in keys]
                for key in prefixed_keys:
                    pipe.get(key)
                result: List[Any] = await pipe.execute()
                values = cast(List[Optional[RedisValue]], result)

                # Build result dictionary
                result_dict: Dict[str, Any] = {}
                for key, value in zip(keys, values):
                    if value is not None and isinstance(value, bytes):
                        result_dict[key] = self._serializer.loads(value.decode())
                return result_dict
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
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                # Set values using pipeline
                pipe = conn.pipeline()
                for key, value in mapping.items():
                    pipe.set(
                        self._prefix_key(key),
                        self._serializer.dumps(value),
                        ex=ttl or self._ttl,
                    )
                await pipe.execute()
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
            pool = await self.get_pool()
            async with RedisConnectionManager(pool) as conn:
                # Delete values using pipeline
                pipe = conn.pipeline()
                for key in keys:
                    pipe.delete(self._prefix_key(key))
                await pipe.execute()
        except Exception as e:
            raise CacheError("Failed to delete multiple values") from e
