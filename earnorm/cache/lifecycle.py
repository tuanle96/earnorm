"""Cache lifecycle management.

This module provides lifecycle management for the cache system, including:
- Initialization and cleanup of cache managers
- Configuration management
- Health checks
- Metrics collection

The lifecycle manager ensures proper initialization and cleanup of cache resources,
and provides a central point for managing cache configuration and state.

Examples:
    ```python
    from earnorm.cache.lifecycle import CacheLifecycleManager

    # Create lifecycle manager with configuration
    manager = CacheLifecycleManager({
        "cache_ttl": "3600",
        "cache_enabled": "true",
        "cache_backend": "redis",
        "cache_host": "localhost",
        "cache_port": "6379",
        "cache_db": "0",
        "cache_min_size": "1",
        "cache_max_size": "10",
        "cache_timeout": "30",
        "cache_max_lifetime": "3600",
        "cache_idle_timeout": "300",
        "cache_validate_on_borrow": "true",
        "cache_test_on_return": "false"
    })

    # Initialize manager
    await manager.init()

    # Get cache manager
    cache = manager.manager
    if cache and cache.is_connected:
        await cache.set("key", "value")

    # Cleanup on shutdown
    await manager.destroy()
    ```
"""

import logging
from typing import Dict, Optional

from earnorm.cache.backends.base import CacheBackend
from earnorm.cache.core.manager import CacheManager
from earnorm.di.lifecycle import LifecycleAware

logger = logging.getLogger(__name__)


class CacheLifecycleManager(LifecycleAware):
    """Cache lifecycle manager implementation."""

    def __init__(self, config: Dict[str, str]) -> None:
        """Initialize manager.

        Args:
            config: Cache configuration.

        Examples:
            ```python
            manager = CacheLifecycleManager({
                "cache_ttl": "3600",
                "cache_enabled": "true",
                "cache_backend": "redis",
                "cache_host": "localhost",
                "cache_port": "6379",
                "cache_db": "0"
            })
            await manager.init()
            ```
        """
        self._config = config
        self._manager: Optional[CacheManager] = None
        self._backend: Optional[CacheBackend] = None
        self._default_ttl = int(config.get("cache_ttl", "3600"))
        self._enabled = config.get("cache_enabled", "true").lower() == "true"

    async def init(self) -> None:
        """Initialize manager."""
        if not self._enabled:
            return

        # Create backend
        backend_type = self._config.get("cache_backend", "redis")
        if backend_type == "redis":
            from earnorm.cache.backends.redis import RedisBackend
            from earnorm.pool.factory import PoolFactory

            # Create Redis pool
            pool = await PoolFactory.create_redis_pool(
                host=self._config.get("cache_host", "localhost"),
                port=int(self._config.get("cache_port", "6379")),
                db=int(self._config.get("cache_db", "0")),
                password=self._config.get("cache_password"),
                username=self._config.get("cache_username"),
                ssl=self._config.get("cache_ssl", "false").lower() == "true",
                encoding=self._config.get("cache_encoding", "utf-8"),
                decode_responses=True,
                min_size=int(self._config.get("cache_min_size", "1")),
                max_size=int(self._config.get("cache_max_size", "10")),
                timeout=int(self._config.get("cache_timeout", "30")),
                max_lifetime=int(self._config.get("cache_max_lifetime", "3600")),
                idle_timeout=int(self._config.get("cache_idle_timeout", "300")),
                validate_on_borrow=self._config.get(
                    "cache_validate_on_borrow", "true"
                ).lower()
                == "true",
                test_on_return=self._config.get("cache_test_on_return", "false").lower()
                == "true",
            )

            # Create Redis backend
            self._backend = RedisBackend(pool)

        if not self._backend:
            return

        # Create manager
        self._manager = CacheManager(
            backend=self._backend, default_ttl=self._default_ttl, enabled=self._enabled
        )

        # Initialize manager
        await self._manager.init()

    async def destroy(self) -> None:
        """Destroy manager."""
        if self._manager:
            await self._manager.destroy()
            self._manager = None

    @property
    def id(self) -> Optional[str]:
        """Get manager ID."""
        return "cache"

    @property
    def data(self) -> Dict[str, str]:
        """Get manager data."""
        return {
            "enabled": str(self._enabled).lower(),
            "default_ttl": str(self._default_ttl),
            "backend": self._config.get("cache_backend", "redis"),
            "host": self._config.get("cache_host", "localhost"),
            "port": self._config.get("cache_port", "6379"),
            "db": self._config.get("cache_db", "0"),
        }

    @property
    def manager(self) -> Optional[CacheManager]:
        """Get cache manager instance."""
        return self._manager
