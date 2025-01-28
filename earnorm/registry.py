"""Registry module for EarnORM.

This module provides centralized registration for all EarnORM services.
It ensures services are registered in the correct order based on dependencies.

Examples:
    ```python
    from earnorm.config import SystemConfig
    from earnorm.registry import register_all

    config = await SystemConfig.get_instance()
    await register_all(config)
    ```
"""

from typing import Any, Dict, TypeVar, cast

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None

from earnorm.base.database.adapters.mongo import MongoAdapter
from earnorm.base.env import Environment
from earnorm.config import SystemConfig
from earnorm.di import container
from earnorm.pool import PoolRegistry, create_mongo_pool, create_redis_pool
from earnorm.pool.protocols.pool import AsyncPoolProtocol

# Type hints for MongoDB
DB = AsyncIOMotorDatabase[Dict[str, Any]]
COLL = AsyncIOMotorCollection[Dict[str, Any]]

# Type vars for pools
DBType = TypeVar("DBType")  # pylint: disable=invalid-name
CollType = TypeVar("CollType")  # pylint: disable=invalid-name


async def register_core_services() -> None:
    """Register core DI services.

    This includes:
    - ServiceManager
    - FactoryManager
    - LifecycleManager
    - DependencyResolver
    """
    from earnorm.di import (
        DependencyResolver,
        FactoryManager,
        LifecycleManager,
        ServiceManager,
    )

    container.register("service_manager", ServiceManager())
    container.register("factory_manager", FactoryManager())
    container.register("lifecycle_manager", LifecycleManager())
    container.register("dependency_resolver", DependencyResolver())


async def register_environment_services(config: SystemConfig) -> None:
    """Register environment and related services.

    This includes:
    - Environment singleton
    - Model registry
    - Transaction manager
    """
    # Create and initialize environment
    env = Environment.get_instance()
    await env.init(config)

    # Register in container
    container.register("environment", env)


async def register_database_services(config: SystemConfig) -> None:
    """Register database services.

    This includes:
    - MongoDB adapter and pool
    """
    # Register MongoDB adapter
    container.register("mongodb", MongoAdapter)

    if not config.database_uri or not config.database_name:
        return

    # Create and register MongoDB pool
    mongo_pool = cast(
        AsyncPoolProtocol[DB, COLL],
        await create_mongo_pool(
            uri=config.database_uri or "",
            database=config.database_name,
            min_size=int(config.database_max_pool_size),
            max_size=int(config.database_max_pool_size),
            validate_on_borrow=bool(config.database_validate_on_borrow),
            test_on_return=bool(config.database_test_on_return),
        ),
    )
    await mongo_pool.init()
    PoolRegistry.register("mongodb", mongo_pool)


async def register_pool_services(config: SystemConfig) -> None:
    """Register connection pool services.

    This includes:
    - MongoDB connection pool
    - Redis pool for event system
    """
    if not config.redis_host or not config.redis_port or not config.redis_db:
        return

    # Create Redis pool for event and cache system
    redis_pool = cast(
        AsyncPoolProtocol[Redis, None],
        await create_redis_pool(
            host=config.redis_host or "localhost",
            port=int(config.redis_port or 6379),
            db=int(config.redis_db or 0),
            min_size=int(config.redis_min_pool_size or 1),
            max_size=int(config.redis_max_pool_size or 10),
            timeout=int(config.redis_pool_timeout or 10),
        ),
    )

    # Register pools
    PoolRegistry.register("redis", redis_pool)

    # Initialize pools
    await redis_pool.init()


async def register_cache_services(config: SystemConfig) -> None:
    """Register cache services.

    This includes:
    - Cache manager
    """
    from earnorm.cache.core.manager import CacheManager

    # Register cache manager
    container.register(
        "cache_manager",
        CacheManager(container=container, ttl=int(config.cache_ttl)),
    )


async def register_all(config: SystemConfig) -> None:
    """Register all services in correct order.

        Args:
        config: System configuration instance

    This function registers services in the following order:
    1. Core DI services
    2. Environment services
    3. Database services
    4. Pool services
    5. Cache services
    6. Event services
    7. Validator services

    Examples:
        ```python
        config = await SystemConfig.get_instance()
        await register_all(config)
        ```
    """
    # 1. Core DI services
    await register_core_services()

    # 2. Environment services
    await register_environment_services(config)

    # 3. Database services
    await register_database_services(config)

    # 4. Pool services
    await register_pool_services(config)

    # 5. Cache services
    await register_cache_services(config)


__all__ = ["register_all"]
