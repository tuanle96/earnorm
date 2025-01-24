"""EarnORM initialization.

This module provides the main entry point for EarnORM.
It initializes the DI container, database registry and system configuration.

Examples:
    ```python
    from earnorm import init

    # Initialize with default settings
    await init()

    # Initialize with custom settings
    await init(
        mongo_uri="mongodb://localhost:27017",
        database="myapp",
        mongo_min_pool_size=5,
        mongo_max_pool_size=20
    )
    ```
"""

import logging
from typing import Any, Optional

from earnorm.config import SystemConfig
from earnorm.di import init_container
from earnorm.registry import register_all

logger = logging.getLogger(__name__)


async def init(
    *,
    mongo_uri: Optional[str] = None,
    database: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Initialize EarnORM.

    This function initializes EarnORM by:
    1. Loading system configuration
    2. Initializing DI container
    3. Registering all services

    Args:
        mongo_uri: MongoDB connection URI
        database: Database name
        **kwargs: Additional configuration options
            - mongo_min_pool_size: Minimum pool size
            - mongo_max_pool_size: Maximum pool size
            - mongo_timeout: Connection timeout
            - mongo_max_lifetime: Maximum connection lifetime
            - mongo_idle_timeout: Connection idle timeout
            - mongo_validate_on_borrow: Whether to validate connections on borrow
            - mongo_test_on_return: Whether to test connections on return
            - redis_host: Redis host
            - redis_port: Redis port
            - redis_db: Redis database
            - cache_backend: Cache backend type
            - cache_ttl: Default cache TTL
    """
    # Load system configuration
    config = await SystemConfig.get_instance()
    if mongo_uri:
        config.mongodb_uri = mongo_uri
    if database:
        config.mongodb_database = database

    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    await config.save()

    # Initialize DI container
    await init_container()

    # Register all services
    await register_all(config)

    logger.info("EarnORM initialized successfully")


__all__ = ["init"]
