"""Cache implementation for EarnORM."""

from typing import Any, Dict, Optional


class Cache:
    """Cache implementation.

    Provides caching functionality with TTL support.
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """Initialize cache.

        Args:
            default_ttl: Default time to live in seconds
        """
        self._cache: Dict[str, Any] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds, defaults to default_ttl
        """
        self._cache[key] = value

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        self._cache.pop(key, None)

    def invalidate_all(self) -> None:
        """Invalidate all cached values."""
        self._cache.clear()

    def has(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        return key in self._cache
