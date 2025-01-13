"""Cache manager for EarnORM."""

from typing import Dict

from .cache import Cache


class CacheManager:
    """Cache manager for EarnORM.

    Manages caching functionality across the application.
    """

    def __init__(self) -> None:
        """Initialize cache manager."""
        self._caches: Dict[str, Cache] = {}
        self._default_ttl: int = 300  # 5 minutes

    def get_cache(self, name: str) -> Cache:
        """Get cache by name.

        Args:
            name: Cache name

        Returns:
            Cache instance
        """
        if name not in self._caches:
            self._caches[name] = Cache(default_ttl=self._default_ttl)
        return self._caches[name]

    def set_default_ttl(self, ttl: int) -> None:
        """Set default TTL for new caches.

        Args:
            ttl: Time to live in seconds
        """
        self._default_ttl = ttl

    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self._caches.values():
            cache.invalidate_all()

    def remove_cache(self, name: str) -> None:
        """Remove cache by name.

        Args:
            name: Cache name
        """
        if name in self._caches:
            self._caches[name].invalidate_all()
            del self._caches[name]

    async def init(self) -> None:
        """Initialize cache manager."""
        pass

    async def start(self) -> None:
        """Start cache manager."""
        pass

    async def stop(self) -> None:
        """Stop cache manager."""
        self.clear_all()

    async def cleanup(self) -> None:
        """Clean up cache manager."""
        self._caches.clear()
