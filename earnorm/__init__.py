"""EarnORM - Async MongoDB ORM.

This module provides the main entry point for EarnORM, including:
- Initialization and configuration
- Connection pool management with multiple backend support (MongoDB, Redis)
- Dependency injection
- Registry management
- Cache system
- Event system

Examples:
    ```python
    import earnorm
    from earnorm import fields, models
    from earnorm.pool import PoolFactory, ConnectionContext

    # Define model
    class User(models.BaseModel):
        # Collection configuration
        _collection = "users"
        _name = "user"
        _indexes = [{"email": 1}]

        # Fields
        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)
        age = fields.Int(required=True)

    # Initialize with MongoDB and Redis
    await earnorm.init(
        pools=[
            await PoolFactory.create_mongo_pool(
                uri="mongodb://localhost:27017",
                database="earnorm_example",
                min_size=5,
                max_size=20
            ),
            await PoolFactory.create_redis_pool(
                host="localhost",
                port=6379,
                db=0,
                min_size=5,
                max_size=20
            )
        ],
        cache_config={
            "ttl": 3600,
            "prefix": "earnorm:",
            "max_retries": 3
        },
        event_config={
            "queue_name": "earnorm:events",
            "batch_size": 100
        }
    )

    # Create users
    users = [
        User(name="John Doe", email="john@example.com", age=30),
        User(name="Jane Smith", email="jane@example.com", age=25),
        User(name="Bob Wilson", email="bob@example.com", age=35),
    ]
    async with ConnectionContext(earnorm.pool_registry.get("mongodb")) as conn:
        for user in users:
            await user.save()

    # Search users using domain
    users = await User.search([("age", ">", 25)])
    for user in users:
        print(f"{user.name} ({user.email}, {user.age} years old)")

    # Find single user
    user = await User.find_one([("email", "=", "john@example.com")])
    if user.exists():
        record = user.ensure_one()
        print(f"Found user: {record.name}, {record.age} years old")

    # Update user
    if user.exists():
        record = user.ensure_one()
        await record.write({"age": 31})
        print(f"Updated age to: {record.age}")

    # Delete users
    all_users = await User.search([])
    for user in all_users:
        await user.delete()

    # Use Redis for caching
    async with ConnectionContext(earnorm.pool_registry.get("redis")) as conn:
        await conn.execute("set", "user:count", len(users))
        count = await conn.execute("get", "user:count")
        print(f"Total users: {count}")
    ```
"""

__author__ = "EarnORM"
__credits__ = "EarnORM"

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Type, Union, cast

# Core imports
from earnorm import fields
from earnorm.base import model as models
from earnorm.base.registry import Registry

# Cache imports
from earnorm.cache import CacheManager
from earnorm.cache.backends.redis import RedisBackend

# DI imports
from earnorm.di import Container

# Event imports
from earnorm.events.manager import EventManager

# Pool imports
from earnorm.pool import (
    MongoConnection,
    MongoPool,
    PoolFactory,
    PoolRegistry,
    RedisConnection,
    RedisPool,
)
from earnorm.pool.core import BaseConnection, BasePool

logger = logging.getLogger(__name__)

# Global variables
env: Optional[Registry] = None
registry: Optional[Registry] = None
di: Optional[Container] = None
pool_registry: Optional[PoolRegistry] = None
pool_factory: Optional[PoolFactory] = None
cache: Optional[CacheManager] = None
events: Optional[EventManager] = None

# Global container instance
container: Container = Container()


def get_all_subclasses(cls: Type[models.BaseModel]) -> list[Type[models.BaseModel]]:
    """Get all subclasses of a class recursively.

    This function traverses the inheritance tree of a class and returns all its subclasses.
    It is used internally to register all model classes with the registry.

    Args:
        cls: Base class to get subclasses for

    Returns:
        List of all subclasses

    Examples:
        ```python
        class BaseModel:
            pass

        class User(BaseModel):
            pass

        class Admin(User):
            pass

        subclasses = get_all_subclasses(BaseModel)
        # Returns [User, Admin]
        ```
    """
    all_subclasses: list[Type[models.BaseModel]] = []
    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses


async def _init_container(
    pools: List[Union[MongoPool, RedisPool]],
    **kwargs: Dict[str, Any],
) -> None:
    """Initialize container and core services.

    Args:
        pools: List of connection pools to initialize
        **kwargs: Additional configuration options
    """
    global di, env, registry, pool_registry, pool_factory

    # Initialize pool registry and factory
    pool_registry = PoolRegistry()
    pool_factory = PoolFactory()

    # Initialize and register pools
    for pool in pools:
        if isinstance(pool, MongoPool):
            await pool_registry.create_and_register(
                "mongodb",
                "mongodb",
                uri=pool.uri,
                database=pool.database,
                min_size=pool.min_size,
                max_size=pool.max_size,
                timeout=pool.timeout,
                max_lifetime=pool.max_lifetime,
                idle_timeout=pool.idle_timeout,
            )
        else:  # RedisPool case
            await pool_registry.create_and_register(
                "redis",
                "redis",
                host=pool.host,
                port=pool.port,
                db=pool.db,
                min_size=pool.min_size,
                max_size=pool.max_size,
                timeout=pool.timeout,
                max_lifetime=pool.max_lifetime,
                idle_timeout=pool.idle_timeout,
            )

    # Initialize container
    await container.init(
        pool_registry=pool_registry,
        pool_factory=pool_factory,
        **kwargs,
    )

    # Update global instances
    di = container
    env = cast(Registry, await container.get("registry"))
    registry = env


async def _init_cache(redis_pool: RedisPool, cache_config: Dict[str, Any]) -> None:
    """Initialize cache system.

    Args:
        redis_pool: Redis pool instance
        cache_config: Cache configuration options
    """
    global cache, di

    # Create Redis backend with pool
    redis_backend = RedisBackend(pool=redis_pool)

    # Initialize cache manager
    cache = CacheManager(
        backend=redis_backend,
        **cache_config,
    )

    # Register with container
    if di is not None:
        container.register("cache", cache)


async def _init_events(redis_pool: RedisPool, event_config: Dict[str, Any]) -> None:
    """Initialize event system.

    Args:
        redis_pool: Redis pool instance
        event_config: Event configuration options
    """
    global events, di, env

    if env is None:
        raise RuntimeError("Environment not initialized")

    # Initialize event manager with env
    events = EventManager(env)

    # Configure event manager
    await events.init(
        backend={
            "host": redis_pool.host,
            "port": redis_pool.port,
            "db": redis_pool.db,
        },
        **event_config,
    )

    # Register with container
    if di is not None:
        container.register("events", events)


async def init(config_path: str) -> None:
    """Initialize EarnORM with config file.

    Args:
        config_path: Path to config file (.yaml, .env, etc)

    Examples:
        >>> await earnorm.init("config.yaml")
    """
    # Initialize registry and config
    global env, registry, di, pool_registry, pool_factory, cache, events

    # Create and initialize registry
    env = Registry()
    registry = env

    # Load config
    await env.init_config(config_path)

    # Initialize pools from config
    pools = []

    # Create MongoDB pool
    mongo_pool = await PoolFactory.create_mongo_pool(
        uri=env.config.mongo_uri,
        database=env.config.mongo_database,
        min_size=env.config.mongo_min_pool_size,
        max_size=env.config.mongo_max_pool_size,
        timeout=env.config.mongo_timeout,
        max_lifetime=env.config.mongo_max_lifetime,
        idle_timeout=env.config.mongo_idle_timeout,
    )
    pools.append(mongo_pool)

    # Create Redis pool
    redis_pool = await PoolFactory.create_redis_pool(
        host=env.config.redis_host,
        port=env.config.redis_port,
        db=env.config.redis_db,
        min_size=env.config.redis_min_pool_size,
        max_size=env.config.redis_max_pool_size,
        timeout=env.config.redis_timeout,
    )
    pools.append(redis_pool)

    # Initialize container and core services
    await _init_container(pools)

    # Initialize cache if enabled
    if env.config.cache_enabled:
        await _init_cache(
            redis_pool=redis_pool,
            cache_config={
                "ttl": env.config.cache_ttl,
                "prefix": env.config.cache_prefix,
                "max_retries": env.config.cache_max_retries,
            },
        )

    # Initialize events if enabled
    if env.config.event_enabled:
        await _init_events(
            redis_pool=redis_pool,
            event_config={
                "queue_name": env.config.event_queue,
                "batch_size": env.config.event_batch_size,
            },
        )

    # Register all model classes
    for model_cls in get_all_subclasses(models.BaseModel):
        env.register_model(model_cls)

    logger.info("EarnORM initialized successfully")


@asynccontextmanager
async def get_connection(
    backend: str = "mongodb",
) -> AsyncIterator[Union[MongoConnection, RedisConnection]]:
    """Get connection from pool.

    This function acquires a connection from the specified backend pool.
    The connection will be automatically released when the context exits.

    Args:
        backend: Backend type ("mongodb" or "redis", default: "mongodb")

    Returns:
        Connection instance from the pool

    Raises:
        RuntimeError: If EarnORM is not initialized
        ValueError: If backend type is invalid
        KeyError: If pool for specified backend is not found

    Examples:
        ```python
        # Get MongoDB connection
        async with earnorm.get_connection("mongodb") as conn:
            await conn.client.find_one(...)

        # Get Redis connection
        async with earnorm.get_connection("redis") as conn:
            await conn.execute("get", "key")
        ```
    """
    if pool_registry is None:
        raise RuntimeError("EarnORM not initialized")

    pool = pool_registry.get(backend)
    if pool is None:
        raise KeyError(f"Pool for backend '{backend}' not found")

    conn = await pool.acquire()
    try:
        yield conn
    finally:
        # Type check to ensure correct connection type
        if backend == "mongodb" and isinstance(conn, MongoConnection):
            await cast(MongoPool, pool).release(conn)
        elif backend == "redis" and isinstance(conn, RedisConnection):
            await cast(RedisPool, pool).release(conn)
        else:
            logger.error(f"Invalid connection type for backend {backend}")


# Public API
__all__ = [
    # Core
    "init",
    "models",
    "fields",
    # Pool
    "get_connection",
    "BasePool",
    "BaseConnection",
    "MongoPool",
    "MongoConnection",
    "RedisPool",
    "RedisConnection",
    # DI and Registry
    "di",
    "env",
    "registry",
    "Container",
    # Cache
    "cache",
    "CacheManager",
    # Events
    "events",
    "EventManager",
]
