"""EarnORM - Async MongoDB ORM."""

__version__ = "0.1.0"
__author__ = "EarnORM"
__credits__ = "EarnORM"

import logging
from typing import Any, Dict, Optional, Type

from earnorm import fields
from earnorm.base import model as models
from earnorm.cache import CacheManager
from earnorm.di import Container, DIContainer
from earnorm.events import EventBus
from earnorm.pool.core.connection import Connection

logger = logging.getLogger(__name__)

# Global variables
env: Any = None
registry: Any = None
di: Optional[DIContainer] = None
pool: Any = None
cache: Optional[CacheManager] = None
event_bus: Optional[EventBus] = None

# Global container instance
container = DIContainer()


def get_all_subclasses(cls: Type[models.BaseModel]) -> list[Type[models.BaseModel]]:
    """Get all subclasses of a class recursively."""
    all_subclasses: list[Type[models.BaseModel]] = []
    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses


async def init(
    mongo_uri: str,
    database: str,
    *,
    redis_uri: Optional[str] = None,
    min_pool_size: int = 5,
    max_pool_size: int = 20,
    pool_timeout: float = 30.0,
    pool_max_lifetime: int = 3600,
    pool_idle_timeout: int = 300,
    cache_config: Optional[dict[str, Any]] = None,
    event_config: Optional[dict[str, Any]] = None,
    **kwargs: Dict[str, Any],
) -> None:
    """Initialize EarnORM with configuration.

    Args:
        mongo_uri: MongoDB connection URI
        database: Database name
        redis_uri: Redis connection URI for caching (optional)
        min_pool_size: Minimum connection pool size
        max_pool_size: Maximum connection pool size
        pool_timeout: Connection acquire timeout
        pool_max_lifetime: Maximum connection lifetime
        pool_idle_timeout: Maximum idle time
        cache_config: Cache configuration options
            - ttl: Default TTL in seconds (default: 3600)
            - prefix: Key prefix (default: "earnorm:")
            - max_retries: Max reconnection attempts (default: 3)
            - retry_delay: Initial delay between retries (default: 1.0)
            - health_check_interval: Health check interval in seconds (default: 30.0)
        event_config: Event configuration options
            - queue_name: Event queue name (default: "earnorm:events")
            - batch_size: Event batch size (default: 100)
            - poll_interval: Event poll interval in seconds (default: 1.0)
            - max_retries: Event max retries (default: 3)
            - retry_delay: Event retry delay in seconds (default: 5.0)
            - num_workers: Event worker count (default: 1)
    """
    global env, registry, di, pool, cache, event_bus

    # Initialize container with pool configuration
    await container.init(
        mongo_uri=mongo_uri,
        database=database,
        min_pool_size=min_pool_size,
        max_pool_size=max_pool_size,
        pool_timeout=pool_timeout,
        pool_max_lifetime=pool_max_lifetime,
        pool_idle_timeout=pool_idle_timeout,
        **kwargs,
    )

    # Update global instances
    di = container
    env = container.registry
    registry = env
    pool = container.pool

    # Initialize services as needed
    if redis_uri:

        # Initialize cache manager
        cache_config = cache_config or {}
        cache_manager = CacheManager(
            redis_uri=redis_uri,
            ttl=cache_config.get("ttl", 3600),
            prefix=cache_config.get("prefix", "earnorm:"),
            max_retries=cache_config.get("max_retries", 3),
            retry_delay=cache_config.get("retry_delay", 1.0),
            health_check_interval=cache_config.get("health_check_interval", 30.0),
        )
        await cache_manager.connect()
        cache = cache_manager
        di.register("cache_manager", cache_manager)
        logger.info("Cache system initialized")

        # Initialize event bus
        event_config = event_config or {}
        event_bus = EventBus(
            redis_uri=redis_uri,
            queue_name=event_config.get("queue_name", "earnorm:events"),
            **event_config,
        )
        await event_bus.connect()
        di.register("event_bus", event_bus)
        logger.info("Event system initialized")

    # Get all subclasses of BaseModel
    for model_cls in get_all_subclasses(models.BaseModel):
        registry.register_model(model_cls)


async def get_connection() -> Connection:
    """Get connection from pool.

    Returns:
        Connection instance
    """
    if pool is None:
        raise RuntimeError("EarnORM not initialized")
    return await pool.acquire()


async def release_connection(conn: Connection) -> None:
    """Release connection back to pool.

    Args:
        conn: Connection to release
    """
    if pool is None:
        raise RuntimeError("EarnORM not initialized")
    await pool.release(conn)


__all__ = [
    "models",
    "init",
    "fields",
    # Pool
    "get_connection",
    "release_connection",
    # DI and Registry
    "di",
    "env",
    "registry",
    "Container",
    # Cache
    "cache",
    "CacheManager",
    # Events
    "event_bus",
]
