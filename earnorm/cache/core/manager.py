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

import hashlib
import logging
from typing import Any, Dict, List, Optional, Type, Union

from earnorm.cache.core.backend import BaseCacheBackend
from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.cache.serializers.json import JsonSerializer
from earnorm.exceptions import CacheError

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
    - Query result caching
    - Model data caching

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

        # Model caching
        await cache.set_model("user", "123", {"name": "John"})
        user = await cache.get_model("user", "123")

        # Query caching
        query_hash = cache.get_query_hash({"age": {"$gt": 18}})
        await cache.set_query("user", query_hash, [{"id": "1"}], limit=10)
        results = await cache.get_query("user", query_hash, limit=10)
        ```
    """

    def __init__(
        self,
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
            raise CacheError(
                f"Unsupported backend type: {backend_type}", backend="redis"
            )

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
                self._backend = backend_class(
                    serializer=serializer, prefix=self._prefix, ttl=self._ttl
                )
            except Exception as e:
                raise CacheError("Failed to initialize backend", backend="redis") from e
        return self._backend

    def _get_backend_class(self) -> Type[BaseCacheBackend]:
        """Get backend class.

        Returns:
            Type[BaseCacheBackend]: Backend class

        Raises:
            CacheError: If backend type is not supported
        """
        if self._backend_type == "redis":
            from earnorm.cache.backends.redis import RedisBackend

            return RedisBackend
        raise CacheError(
            f"Unsupported backend type: {self._backend_type}", backend="redis"
        )

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
            raise CacheError("Failed to create serializer", backend="redis") from e

    def get_query_hash(self, query: Dict[str, Any]) -> str:
        """Generate hash for query parameters.

        Args:
            query: Query parameters

        Returns:
            str: Query hash
        """
        # Sort query parameters for consistent hashing
        sorted_query = {str(k): str(v) for k, v in sorted(query.items())}
        query_str = ":".join(f"{k}={v}" for k, v in sorted_query.items())
        return hashlib.md5(query_str.encode()).hexdigest()[:16]

    async def get_model(
        self, model_name: str, record_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get model data from cache.

        Args:
            model_name: Name of the model
            record_id: Record ID

        Returns:
            Optional[Dict[str, Any]]: Model data or None if not found
        """
        key = f"model:{model_name}:record:{record_id}"
        return await self.get(key)

    async def set_model(
        self,
        model_name: str,
        record_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Set model data in cache.

        Args:
            model_name: Name of the model
            record_id: Record ID
            data: Model data
            ttl: Optional TTL in seconds
        """
        key = f"model:{model_name}:record:{record_id}"
        await self.set(key, data, ttl)

    async def get_query(
        self, model_name: str, query_hash: str, **params: Union[str, int]
    ) -> Optional[List[Dict[str, Any]]]:
        """Get query results from cache.

        Args:
            model_name: Name of the model
            query_hash: Query hash
            **params: Additional query parameters (e.g. limit, offset)

        Returns:
            Optional[List[Dict[str, Any]]]: Query results or None if not found
        """
        key = f"query:{model_name}:{query_hash}"
        if params:
            key = f"{key}:" + ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        return await self.get(key)

    async def set_query(
        self,
        model_name: str,
        query_hash: str,
        results: List[Dict[str, Any]],
        ttl: Optional[int] = None,
        **params: Union[str, int],
    ) -> None:
        """Set query results in cache.

        Args:
            model_name: Name of the model
            query_hash: Query hash
            results: Query results
            ttl: Optional TTL in seconds
            **params: Additional query parameters (e.g. limit, offset)
        """
        key = f"query:{model_name}:{query_hash}"
        if params:
            key = f"{key}:" + ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        await self.set(key, results, ttl)

    async def invalidate_model(self, model_name: str, record_id: str) -> None:
        """Invalidate model cache.

        Args:
            model_name: Name of the model
            record_id: Record ID
        """
        key = f"model:{model_name}:record:{record_id}"
        await self.delete(key)

    async def invalidate_query(self, model_name: str) -> None:
        """Invalidate all query results for model.

        Args:
            model_name: Name of the model
        """
        pattern = f"query:{model_name}:*"
        await self.delete(pattern)

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
            return await self.backend.get(key)
        except Exception as e:
            logger.error(f"Failed to get cache value: {str(e)}")
            return None

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
            await self.backend.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Failed to set cache value: {str(e)}")

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key

        Raises:
            CacheError: If failed to delete value
        """
        try:
            await self.backend.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cache value: {str(e)}")

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict[str, Any]: Dictionary of key-value pairs

        Raises:
            CacheError: If failed to get values
        """
        try:
            return await self.backend.get_many(keys)
        except Exception as e:
            logger.error(f"Failed to get multiple cache values: {str(e)}")
            return {}

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
        try:
            await self.backend.set_many(mapping, ttl)
        except Exception as e:
            logger.error(f"Failed to set multiple cache values: {str(e)}")

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple values from cache.

        Args:
            keys: List of cache keys

        Raises:
            CacheError: If failed to delete values
        """
        try:
            await self.backend.delete_many(keys)
        except Exception as e:
            logger.error(f"Failed to delete multiple cache values: {str(e)}")

    async def close(self) -> None:
        """Close cache backend."""
        if self._backend:
            await self._backend.close()

    async def cleanup(self) -> None:
        """Cleanup cache backend."""
        if self._backend:
            await self._backend.cleanup()

    async def queue_write(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """Queue value for asynchronous write to cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds
        """
        try:
            # For now, implement as write-through since queue is not implemented yet
            await self.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Failed to queue cache write: {str(e)}")
