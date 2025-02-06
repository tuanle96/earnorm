"""Registry module for registering services."""

import logging
from typing import TypeVar, cast

from earnorm.base.database.adapters.mongo import MongoAdapter
from earnorm.base.env import Environment
from earnorm.config import SystemConfig
from earnorm.di import container
from earnorm.pool import PoolRegistry, create_mongo_pool
from earnorm.pool.protocols import AsyncPoolProtocol
from earnorm.pool.types import MongoCollectionType, MongoDBType
from earnorm.types.models import ModelProtocol

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

    Args:
        config: System configuration instance
    """
    # Create and initialize environment if not already initialized
    env = Environment.get_instance()
    if not getattr(env, "_initialized", False):
        from earnorm.config.data import SystemConfigData

        # Get config data excluding descriptor fields and metadata
        config_dict = config.model_dump()

        # Create SystemConfigData with raw data
        config_data = SystemConfigData(data=config_dict)
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
        adapter = MongoAdapter[
            ModelProtocol
        ]()  # Use ModelProtocol instead of DatabaseModel
        await adapter.init()
        container.register("mongodb_adapter", adapter)
        # Also register as default database adapter
        container.register("database_adapter", adapter)
        logger.info("MongoDB adapter registered successfully")


async def register_all(config: SystemConfig) -> None:
    """Register all services in the correct order.

    Args:
        config: System configuration object

    The order of registration is important:
    1. Core DI services
    2. Pool services (Redis pool must be registered first)
    3. Cache services (Cache manager needs Redis pool)
    4. Database services (Database adapter must be registered before environment)
    5. Environment services (Environment needs cache manager and database adapter)
    """
    # 1. Core DI services
    logger.info("Registering core services")
    await register_core_services()

    # 4. Database services - Must be registered before environment
    logger.info("Registering database services")
    await register_database_services(config)

    # 5. Environment services - Needs cache manager and database adapter
    logger.info("Registering environment services")
    await register_environment_services(config)

    logger.info("All services registered successfully")


__all__ = ["register_all"]
