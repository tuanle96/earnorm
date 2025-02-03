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

import logging
from typing import TypeVar, cast

from earnorm.base.database.adapters.mongo import MongoAdapter
from earnorm.base.env import Environment
from earnorm.config import SystemConfig
from earnorm.di import container
from earnorm.pool import PoolRegistry, create_mongo_pool, create_redis_pool
from earnorm.pool.protocols import AsyncPoolProtocol
from earnorm.pool.types import MongoCollectionType, MongoDBType, RedisType
from earnorm.types import DatabaseModel

logger = logging.getLogger(__name__)

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

    # Only register if not already registered
    if not container.has("service_manager"):
        container.register("service_manager", ServiceManager())
    if not container.has("factory_manager"):
        container.register("factory_manager", FactoryManager())
    if not container.has("lifecycle_manager"):
        container.register("lifecycle_manager", LifecycleManager())
    if not container.has("dependency_resolver"):
        container.register("dependency_resolver", DependencyResolver())


async def register_environment_services(config: SystemConfig) -> None:
    """Register environment and related services.

    This includes:
    - Environment singleton
    - Model registry
    - Transaction manager
    """
    # Create and initialize environment if not already initialized
    env = Environment.get_instance()
    if not getattr(env, "_initialized", False):
        from earnorm.config.data import SystemConfigData

        config_data = SystemConfigData(**config.model_dump())
        await env.init(config_data)

    # Register in container if not already registered
    if not container.has("environment"):
        container.register("environment", env)


async def register_database_services(config: SystemConfig) -> None:
    """Register database services.

    This includes:
    - MongoDB adapter and pool
    """
    # Skip if no database config
    if not config.database_uri or not config.database_name:
        return

    # Create and register MongoDB pool if not exists
    if not container.has("mongodb_pool"):
        mongo_pool = cast(
            AsyncPoolProtocol[MongoDBType, MongoCollectionType],
            await create_mongo_pool(
                uri=config.database_uri or "",
                database=config.database_name,
                min_size=int(config.database_options.get("min_pool_size") or 1),
                max_size=int(config.database_options.get("max_pool_size") or 10),
            ),
        )
        await mongo_pool.init()
        PoolRegistry.register("mongodb", mongo_pool)
        container.register("mongodb_pool", mongo_pool)

    # Register MongoDB adapter if not exists
    if not container.has("mongodb_adapter"):
        adapter = MongoAdapter[DatabaseModel]()
        await adapter.init()
        container.register("mongodb_adapter", adapter)


async def register_pool_services(config: SystemConfig) -> None:
    """Register connection pool services.

    This includes:
    - Redis pool for event system
    """
    # Skip if no Redis config
    if not config.redis_host or not config.redis_port or not config.redis_db:
        return

    # Create and register Redis pool if not exists
    if not container.has("redis_pool"):
        redis_pool = cast(
            AsyncPoolProtocol[RedisType, None],
            await create_redis_pool(
                host=config.redis_host or "localhost",
                port=int(config.redis_port or 6379),
                db=int(config.redis_db or 0),
                min_size=int(config.redis_min_pool_size or 1),
                max_size=int(config.redis_max_pool_size or 10),
                timeout=int(config.redis_pool_timeout or 10),
            ),
        )
        await redis_pool.init()
        PoolRegistry.register("redis", redis_pool)
        container.register("redis_pool", redis_pool)


async def register_cache_services(config: SystemConfig) -> None:
    """Register cache services.

    This includes:
    - Cache manager
    """
    from earnorm.cache.core.manager import CacheManager

    # Register cache manager if not exists
    if not container.has("cache_manager"):
        container.register(
            "cache_manager",
            CacheManager(ttl=int(config.cache_ttl or 60)),
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

    Examples:
        ```python
        config = await SystemConfig.get_instance()
        await register_all(config)
        ```
    """
    logger.info("Registering core services")
    await register_core_services()

    logger.info("Registering environment services")
    await register_environment_services(config)

    logger.info("Registering database services")
    await register_database_services(config)

    logger.info("Registering pool services")
    await register_pool_services(config)

    logger.info("Registering cache services")
    await register_cache_services(config)

    logger.info("All services registered successfully")


__all__ = ["register_all"]
