"""Cache module for EarnORM.

This module provides caching functionality for EarnORM, including:
- Cache backends (Redis, etc.)
- Cache manager for high-level operations
- Distributed locking
- Metrics collection
- Decorators for easy caching

The module is organized into several submodules:
- backends: Cache backend implementations (Redis, etc.)
- core: Core cache functionality (manager, locks, metrics)
- decorators: Caching decorators (@cached)

Examples:
    ```python
    from earnorm.cache import CacheManager
    from earnorm.cache.backends.redis import RedisBackend
    from earnorm.cache.decorators import cached

    # Initialize cache manager
    cache = CacheManager(
        backend=RedisBackend(host="localhost", port=6379),
        default_ttl=3600,
        enabled=True
    )
    await cache.init()

    # Use cache manager directly
    await cache.set("key", "value", ttl=300)
    value = await cache.get("key")

    # Use caching decorator
    @cached(ttl=300)
    async def get_user(user_id: str) -> dict:
        return await db.users.find_one({"_id": user_id})
    ```

See Also:
    - CacheManager: Main interface for caching operations
    - RedisBackend: Redis cache backend implementation
    - cached: Decorator for caching function results
"""

from earnorm.cache.backends.redis import RedisBackend
from earnorm.cache.core.exceptions import (
    CacheError,
    CacheConnectionError,
    LockError,
    SerializationError,
    ValidationError,
)
from earnorm.cache.core.lock import DistributedLock
from earnorm.cache.core.manager import CacheManager
from earnorm.cache.core.metrics import CacheMetrics, MetricsCollector
from earnorm.cache.decorators.cached import cached

__all__ = [
    # Backends
    "RedisBackend",
    # Core
    "CacheManager",
    "DistributedLock",
    "CacheMetrics",
    "MetricsCollector",
    # Exceptions
    "CacheError",
    "CacheConnectionError",
    "LockError",
    "SerializationError",
    "ValidationError",
    # Decorators
    "cached",
]
