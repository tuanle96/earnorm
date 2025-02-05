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
import time
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from redis.asyncio import Redis
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError

from earnorm.cache.core.backend import BaseCacheBackend
from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.exceptions import CacheError
from earnorm.pool.protocols.pool import AsyncPoolProtocol

logger = logging.getLogger(__name__)

# Define type variables
RedisConn = TypeVar("RedisConn", bound=Redis)
RedisValue = Union[str, bytes, int, float, None]
RedisPipelineResult = List[RedisValue]
RedisScanResult = AsyncIterator[Union[str, bytes]]
RedisKey = Union[str, bytes]


class RedisCommandProtocol(Protocol):
    """Protocol for Redis commands."""

    async def execute_typed(self, command: str, *args: Any, **kwargs: Any) -> Any:
        """Execute Redis command with type hints."""
        ...

    def pipeline(self) -> Pipeline:
        """Get Redis pipeline."""
        ...


class RedisBackend(BaseCacheBackend):
    """Redis cache backend implementation."""

    CACHE_VERSION = "v1"  # Global cache version

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
        self._hit_count: int = 0
        self._miss_count: int = 0

    @property
    def hit_ratio(self) -> float:
        """Get cache hit ratio.

        Returns:
            float: Cache hit ratio between 0 and 1

        Examples:
            >>> cache = RedisBackend()
            >>> cache.hit_ratio
            0.75
        """
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total

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
                    raise CacheError("Invalid Redis pool type", backend="redis")
                self._pool = pool
                logger.info("Redis pool initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Redis pool: %s", str(e))
                raise CacheError("Failed to get Redis pool", backend="redis") from e

    async def get_pool(self) -> AsyncPoolProtocol[Redis, None]:
        """Get Redis pool.

        Returns:
            RedisPool: Redis connection pool

        Raises:
            CacheError: If pool is not initialized or cannot be retrieved
        """
        await self._init_pool()
        if self._pool is None:
            raise CacheError("Redis pool is not initialized", backend="redis")
        return self._pool

    def _get_cache_version(self) -> str:
        """Get current cache version.

        Returns:
            str: Current cache version string
        """
        return self.CACHE_VERSION

    def _get_cache_key(self, key_type: str, *parts: str) -> str:
        """Generate standardized cache key.

        Args:
            key_type: Type of key (model, query, etc)
            parts: Key parts to join

        Returns:
            str: Standardized cache key with prefix and version

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._get_cache_key("model", "user", "123")
            'app:v1:model:user:123'
            >>> backend._get_cache_key("query", "user", "abc123")
            'app:v1:query:user:abc123'
        """
        key = f"{key_type}:{':'.join(parts)}"
        return self._prefix_key(key)

    def _prefix_key(self, key: str) -> str:
        """Add prefix and version to key.

        Args:
            key: Cache key

        Returns:
            str: Prefixed and versioned key

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._prefix_key("user:1")
            'app:v1:user:1'
        """
        # If key already has prefix, return as is
        if key.startswith(f"{self._prefix}:{self._get_cache_version()}:"):
            return key

        # Add prefix and version
        return f"{self._prefix}:{self._get_cache_version()}:{key}"

    def _get_model_key(self, model_name: str, record_id: str) -> str:
        """Generate cache key for model record.

        Args:
            model_name: Name of the model
            record_id: Record ID

        Returns:
            str: Cache key for model record

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._get_model_key("user", "123")
            'app:v1:model:user:record:123'
        """
        return self._get_cache_key("model", model_name, "record", record_id)

    def _get_query_key(self, model_name: str, query_hash: str, **params: str) -> str:
        """Generate cache key for query results.

        Args:
            model_name: Name of the model
            query_hash: Hash of query parameters
            **params: Additional query parameters (e.g. limit, offset)

        Returns:
            str: Cache key for query results

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._get_query_key("user", "abc123", limit="10")
            'app:v1:query:user:abc123:limit:10'
        """
        parts = [model_name, query_hash]
        for k, v in sorted(params.items()):
            parts.extend([k, str(v)])
        return self._get_cache_key("query", *parts)

    def _get_model_pattern(self, model_name: str) -> str:
        """Generate pattern for model keys.

        Args:
            model_name: Name of the model

        Returns:
            str: Pattern for model keys

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._get_model_pattern("user")
            'app:v1:model:user:*'
        """
        return self._get_cache_key("model", model_name, "*")

    def _get_query_pattern(self, model_name: str) -> str:
        """Generate pattern for query keys.

        Args:
            model_name: Name of the model

        Returns:
            str: Pattern for query keys

        Examples:
            >>> backend = RedisBackend(prefix="app")
            >>> backend._get_query_pattern("user")
            'app:v1:query:user:*'
        """
        return self._get_cache_key("query", model_name, "*")

    async def _validate_cache_data(self, key: str, value: Any) -> bool:
        """Validate cache data before setting.

        Args:
            key: Cache key
            value: Value to validate

        Returns:
            bool: True if data is valid, False otherwise
        """
        if value is None:
            logger.warning(f"Attempting to cache None value for key {key}")
            return False

        if isinstance(value, dict):
            if not any(v is not None for v in value.values()):  # type: ignore
                logger.warning(f"All values in dict are None for key {key}")
                return False

        return True

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value or None if not found

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            start_time = time.time()
            pool = await self.get_pool()
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                prefixed_key = self._prefix_key(key)
                value = await redis_conn.execute_typed("get", prefixed_key)
                duration = (time.time() - start_time) * 1000

                if value is None:
                    self._miss_count += 1
                    logger.debug(f"Cache MISS for key '{key}' in {duration:.2f}ms")
                    return None

                self._hit_count += 1
                logger.debug(f"Cache HIT for key '{key}' in {duration:.2f}ms")

                if isinstance(value, bytes):
                    try:
                        result = self._serializer.loads(value.decode())
                        if result is None:
                            # Invalid cache data, remove it
                            logger.warning(
                                f"Invalid cache data for key '{key}', removing..."
                            )
                            await self.delete(key)
                            return None

                        # Validate deserialized data
                        if not await self._validate_cache_data(key, result):
                            logger.warning(
                                f"Invalid cache data format for key '{key}', removing..."
                            )
                            await self.delete(key)
                            return None

                        # Log the actual data for debugging
                        logger.debug(
                            f"Deserialized cache data for key '{key}': {result}"
                        )
                        return result

                    except Exception as e:
                        logger.error(
                            f"Failed to deserialize cache data for key '{key}': {str(e)}"
                        )
                        await self.delete(key)
                        return None

                return None

        except RedisError as e:
            logger.error(f"Redis error in get(): {str(e)}")
            raise CacheError(f"Redis error: {str(e)}", backend="redis") from e

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            # Validate value before serialization
            if not await self._validate_cache_data(key, value):
                logger.warning(f"Invalid cache data for key '{key}', skipping...")
                return

            # Serialize value
            data = self._serializer.dumps(value)
            if not data:
                logger.error(f"Failed to serialize value for key '{key}'")
                return

            start_time = time.time()
            pool = await self.get_pool()
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Set new value
                cache_key = self._prefix_key(key)
                ttl = ttl or self._ttl
                success = await redis_conn.execute_typed("setex", cache_key, ttl, data)

                duration = (time.time() - start_time) * 1000
                if success:
                    logger.debug(f"Cache SET for key '{key}' in {duration:.2f}ms")
                else:
                    logger.warning(f"Failed to set cache for key '{key}'")

        except RedisError as e:
            logger.error(f"Redis error in set(): {str(e)}")
            raise CacheError(f"Redis error: {str(e)}", backend="redis") from e

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            start_time = time.time()
            pool = await self.get_pool()
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Delete all versions
                pattern = self._prefix_key(key)
                deleted = 0
                cursor = "0"

                while True:  # Continue until cursor is 0
                    # Execute scan command for each iteration
                    result = await redis_conn.execute_typed(
                        "scan", cursor, match=pattern
                    )
                    if not result or len(result) != 2:
                        break

                    cursor_result: Tuple[Union[str, bytes], Sequence[RedisKey]] = cast(
                        Tuple[Union[str, bytes], Sequence[RedisKey]], result
                    )
                    cursor, keys = cursor_result
                    cursor = str(cursor)  # Convert cursor to string

                    if isinstance(keys, (list, tuple)):
                        for cache_key in keys:
                            if isinstance(cache_key, bytes):
                                if await redis_conn.execute_typed("delete", cache_key):
                                    deleted += 1

                    if cursor == "0":  # Stop when cursor returns to 0
                        break

                duration = (time.time() - start_time) * 1000
                if deleted > 0:
                    logger.debug(
                        f"Cache DELETE {deleted} keys for '{key}' in {duration:.2f}ms"
                    )

        except RedisError as e:
            logger.error(f"Redis error in delete(): {str(e)}")
            raise CacheError(f"Redis error: {str(e)}", backend="redis") from e

    async def clear(self) -> bool:
        """Clear all cache entries.

        Returns:
            bool: True if cache was cleared successfully

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            start_time = time.time()
            pool = await self.get_pool()
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Delete all keys with prefix
                pattern = self._prefix_key("*")
                deleted = 0
                cursor = "0"

                while True:  # Continue until cursor is 0
                    # Execute scan command for each iteration
                    result = await redis_conn.execute_typed(
                        "scan", cursor, match=pattern
                    )
                    if not result or len(result) != 2:
                        break

                    cursor_result: Tuple[Union[str, bytes], Sequence[RedisKey]] = cast(
                        Tuple[Union[str, bytes], Sequence[RedisKey]], result
                    )
                    cursor, keys = cursor_result
                    cursor = str(cursor)  # Convert cursor to string

                    if isinstance(keys, (list, tuple)):
                        for cache_key in keys:
                            if isinstance(cache_key, bytes):
                                if await redis_conn.execute_typed("delete", cache_key):
                                    deleted += 1

                    if cursor == "0":  # Stop when cursor returns to 0
                        break

                duration = (time.time() - start_time) * 1000
                logger.debug(f"Cache CLEAR {deleted} keys in {duration:.2f}ms")
                return deleted > 0

        except RedisError as e:
            logger.error(f"Redis error in clear(): {str(e)}")
            raise CacheError(f"Redis error: {str(e)}", backend="redis") from e

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
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Get values using pipeline
                pipe = redis_conn.pipeline()
                prefixed_keys = [self._prefix_key(key) for key in keys]
                for key in prefixed_keys:
                    pipe.get(key)
                result = await pipe.execute()  # type: ignore
                values = cast(List[Optional[RedisValue]], result)

                # Build result dictionary
                result_dict: Dict[str, Any] = {}
                for key, value in zip(keys, values):
                    if value is not None and isinstance(value, bytes):
                        result_dict[key] = self._serializer.loads(value.decode())
                return result_dict
        except Exception as e:
            raise CacheError("Failed to get multiple values", backend="redis") from e

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
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Set values using pipeline
                pipe = redis_conn.pipeline()
                for key, value in mapping.items():
                    pipe.set(
                        self._prefix_key(key),
                        self._serializer.dumps(value),
                        ex=ttl or self._ttl,
                    )
                await pipe.execute()
        except Exception as e:
            raise CacheError("Failed to set multiple values", backend="redis") from e

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
            async with await pool.connection() as conn:
                redis_conn = cast(RedisCommandProtocol, conn)
                # Delete values using pipeline
                pipe = redis_conn.pipeline()
                for key in keys:
                    pipe.delete(self._prefix_key(key))
                await pipe.execute()
        except Exception as e:
            raise CacheError("Failed to delete multiple values", backend="redis") from e
