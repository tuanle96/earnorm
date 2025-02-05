"""Core components for EarnORM cache.

This package provides core components for the cache module, including:
- Cache backend protocol
- Cache manager
- Cache metrics
- Cache exceptions
- Cache locks

Examples:
    ```python
    from earnorm.cache.core.backend import CacheBackend
    from earnorm.cache.core.manager import CacheManager
    from earnorm.cache.backends.redis import RedisBackend

    # Create Redis backend
    redis_backend = RedisBackend(pool=redis_pool)

    # Create cache manager
    cache = CacheManager(
        backend=redis_backend,
        default_ttl=3600,
        enabled=True
    )

    # Use cache
    await cache.set("key", "value", ttl=300)
    value = await cache.get("key")
    ```
"""

from earnorm.cache.core.backend import CacheBackendProtocol
from earnorm.cache.core.manager import CacheManager
from earnorm.cache.core.metrics import CacheMetrics
from earnorm.exceptions import CacheError

__all__ = [
    "CacheBackendProtocol",
    "CacheError",
    "CacheManager",
    "CacheMetrics",
]
