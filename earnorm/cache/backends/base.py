"""Base cache backend interface."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from earnorm.di.lifecycle import LifecycleAware


@runtime_checkable
class CacheBackendProtocol(Protocol):
    """Cache backend protocol.

    This protocol defines the core cache operations that all backends must implement.
    Methods are ordered as follows:
    1. Properties (is_connected)
    2. CRUD operations (get, set, delete)
    3. Check operations (exists)
    4. Management operations (clear, scan, info)
    """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if backend is connected.

        Returns:
            bool: True if connected to cache server
        """
        ...

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value if exists, None otherwise
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            bool: True if value was set
        """
        ...

    @abstractmethod
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache.

        Args:
            *keys: Cache keys to delete

        Returns:
            int: Number of keys deleted
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            bool: True if key exists
        """
        ...

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all keys from cache.

        Returns:
            bool: True if cache was cleared
        """
        ...

    @abstractmethod
    async def scan(self, pattern: str) -> List[str]:
        """Scan keys matching pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            List[str]: List of matching keys
        """
        ...

    @abstractmethod
    async def info(self) -> Dict[str, str]:
        """Get backend info.

        Returns:
            Dict[str, str]: Backend information
        """
        ...


class CacheBackend(CacheBackendProtocol, LifecycleAware):
    """Base cache backend implementation.

    This class provides a base implementation for cache backends.
    It implements the CacheBackendProtocol and LifecycleAware protocols.

    Examples:
        ```python
        class RedisBackend(CacheBackend):
            def __init__(self, pool: RedisPool) -> None:
                self._pool = pool

            @property
            def is_connected(self) -> bool:
                return self._pool.available > 0

            async def get(self, key: str) -> Optional[Any]:
                conn = await self._pool.acquire()
                try:
                    value = await conn.execute("get", key)
                    if value is not None:
                        return loads(value)
                    return None
                finally:
                    await self._pool.release(conn)

            # ... implement other methods ...
        ```
    """

    @property
    def id(self) -> Optional[str]:
        """Get backend ID."""
        return None

    @property
    def data(self) -> Dict[str, str]:
        """Get backend data."""
        return {}

    async def init(self) -> None:
        """Initialize backend."""
        pass

    async def destroy(self) -> None:
        """Destroy backend."""
        pass
