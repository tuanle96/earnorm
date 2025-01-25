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

from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.backends import MongoBackend
from earnorm.config import SystemConfig
from earnorm.di import container
from earnorm.pool import PoolRegistry, create_mongo_pool, create_redis_pool

# Type hints for MongoDB
DB = AsyncIOMotorDatabase[Dict[str, Any]]
COLL = AsyncIOMotorCollection[Dict[str, Any]]


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


async def register_database_services(config: SystemConfig) -> None:
    """Register database services.

    This includes:
    - MongoDB backend
    - Database registry
    """
    from earnorm.base.registry import DatabaseRegistry

    # Register backend
    container.register("mongodb", MongoBackend)

    # Register database registry
    registry = DatabaseRegistry()
    container.register("database_registry", registry)

    # Initialize with MongoDB
    await registry.switch(
        "mongodb",
        uri=str(config.mongodb_uri),
        database=str(config.mongodb_database),
        min_pool_size=int(config.mongodb_min_pool_size),
        max_pool_size=int(config.mongodb_max_pool_size),
    )


async def register_pool_services(config: SystemConfig) -> None:
    """Register connection pool services.

    This includes:
    - MongoDB connection pool
    - Redis pool for event system
    """
    # Create MongoDB pool
    mongo_pool = await create_mongo_pool(
        uri=str(config.mongodb_uri),
        database=str(config.mongodb_database),
        min_size=int(config.mongodb_min_pool_size),
        max_size=int(config.mongodb_max_pool_size),
        timeout=int(config.mongodb_pool_timeout),
        max_lifetime=int(config.mongodb_max_lifetime),
        idle_timeout=int(config.mongodb_idle_timeout),
        validate_on_borrow=bool(config.mongodb_validate_on_borrow),
        test_on_return=bool(config.mongodb_test_on_return),
    )

    # Create Redis pool for event and cache system
    redis_pool = await create_redis_pool(
        host=str(config.redis_host),
        port=int(config.redis_port),
        db=int(config.redis_db),
        min_size=int(config.redis_min_pool_size),
        max_size=int(config.redis_max_pool_size),
        timeout=int(config.redis_pool_timeout),
    )

    # Register pools
    PoolRegistry.register("mongodb", mongo_pool)
    PoolRegistry.register("redis", redis_pool)

    # Initialize pools
    await mongo_pool.init()
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


async def register_event_services() -> None:
    """Register event services.

    This includes:
    - Event registry
    - Default handlers
    - Default event types
    """
    from earnorm.events.core.registry import EventRegistry
    from earnorm.events.handlers import CreateUserHandler, UserHandler

    registry = EventRegistry()

    # Register default handlers
    registry.register("user.*", UserHandler())
    registry.register("user.created", CreateUserHandler())

    # Register default event types
    registry.register_type("user.created")
    registry.register_type("user.updated")

    container.register("event_registry", registry)


async def register_validator_services() -> None:
    """Register validator services.

    This includes:
    - Validator registry
    - Default validators
    """
    from earnorm.fields.validators.registry import (
        RangeValidator,
        RegexValidator,
        RequiredValidator,
        TypeValidator,
        ValidatorRegistry,
    )

    registry = ValidatorRegistry()
    registry.register("required", RequiredValidator)
    registry.register("type", TypeValidator)
    registry.register("range", RangeValidator)
    registry.register("regex", RegexValidator)

    container.register("validator_registry", registry)


async def register_all(config: SystemConfig) -> None:
    """Register all services in correct order.

    Args:
        config: System configuration instance

    This function registers services in the following order:
    1. Core DI services
    2. Database services
    3. Pool services
    4. Cache services
    5. Event services
    6. Validator services

    Examples:
        ```python
        config = await SystemConfig.get_instance()
        await register_all(config)
        ```
    """
    # 1. Core DI services
    await register_core_services()

    # 2. Database services
    await register_database_services(config)

    # 3. Pool services
    await register_pool_services(config)

    # 4. Cache services
    await register_cache_services(config)

    # 5. Event services
    await register_event_services()

    # 6. Validator services
    await register_validator_services()


__all__ = ["register_all"]
