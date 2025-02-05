"""Cache backend protocol definition.

This module provides protocol for cache backends.

Examples:
    ```python
    from typing import Any, Dict, List, Optional

    from earnorm.cache.core.backend import BaseCacheBackend
    from earnorm.cache.core.serializer import SerializerProtocol

    class MyBackend(BaseCacheBackend):
        async def get(self, key: str) -> Optional[str]:
            return self._storage.get(key)

        async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
            self._storage[key] = self._serializer.dumps(value)

        async def delete(self, key: str) -> None:
            self._storage.pop(key, None)

        async def get_many(self, keys: List[str]) -> Dict[str, Any]:
            result = {}
            for key in keys:
                value = self._storage.get(key)
                if value is not None:
                    result[key] = self._serializer.loads(value)
            return result

        async def set_many(
            self, mapping: Dict[str, Any], ttl: Optional[int] = None
        ) -> None:
            for key, value in mapping.items():
                self._storage[key] = self._serializer.dumps(value)

        async def delete_many(self, keys: List[str]) -> None:
            for key in keys:
                self._storage.pop(key, None)

    # Create backend
    backend = MyBackend(serializer=JsonSerializer())

    # Use backend
    await backend.set("key", "value")
    value = await backend.get("key")
    await backend.delete("key")
    ```
"""

import abc
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from earnorm.cache.core.serializer import SerializerProtocol


@runtime_checkable
class CacheBackendProtocol(Protocol):
    """Protocol for cache backends.

    This protocol defines interface for cache backends.
    All backends must implement this protocol.

    Features:
    - Runtime protocol checking
    - Type hints
    - Error handling
    - Batch operations
    """

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[str]: Cached value or None if not found
        """

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds
        """

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict[str, Any]: Dictionary of key-value pairs
        """
        return {}

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set multiple values in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Optional TTL in seconds
        """

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple values from cache.

        Args:
            keys: List of cache keys
        """

    async def close(self) -> None:
        """Close cache backend."""

    async def cleanup(self) -> None:
        """Cleanup cache backend."""


class BaseCacheBackend(CacheBackendProtocol, abc.ABC):
    """Base class for cache backends.

    This class provides base implementation for cache backends.
    All backends should inherit from this class.

    Features:
    - Abstract base class
    - Type hints
    - Error handling
    - Batch operations
    """

    def __init__(
        self,
        serializer: SerializerProtocol,
        prefix: str = "app",
        ttl: int = 300,
    ) -> None:
        """Initialize cache backend.

        Args:
            serializer: Value serializer
            prefix: Key prefix
            ttl: Default TTL in seconds
        """
        self._serializer = serializer
        self._prefix = prefix
        self._ttl = ttl
        self._storage: Dict[str, str] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value or None if not found
        """
        ...

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        ...

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dict[str, Any]: Dictionary of key-value pairs
        """
        ...

    async def set_many(
        self, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set multiple values in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Optional TTL in seconds
        """
        ...

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple values from cache.

        Args:
            keys: List of cache keys
        """
        ...

    async def close(self) -> None:
        """Close cache backend."""
        ...

    async def cleanup(self) -> None:
        """Cleanup cache backend."""
        ...
