"""Pool registry implementation."""

import logging
from typing import Any, Dict, Optional, Union

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.pool.factory import PoolFactory

logger = logging.getLogger(__name__)


class PoolRegistry:
    """Registry for managing pool instances.

    This registry provides a centralized way to manage pool instances in the application.
    It ensures that pools are properly initialized, tracked, and cleaned up when no
    longer needed.

    Examples:
        ```python
        # Create registry
        registry = PoolRegistry()

        # Create and register MongoDB pool
        mongo_pool = await PoolFactory.create_mongo_pool(
            uri="mongodb://localhost:27017",
            database="test"
        )
        registry.register("mongodb", mongo_pool)

        # Get pool by name
        pool = registry.get("mongodb")
        if pool:
            async with pool.acquire() as conn:
                await conn.execute(...)

        # Close all pools
        await registry.close_all()
        ```
    """

    def __init__(self) -> None:
        """Initialize pool registry."""
        self._pools: Dict[str, Union[MongoPool, RedisPool]] = {}
        self._factory = PoolFactory()

    def register(self, name: str, pool: Union[MongoPool, RedisPool]) -> None:
        """Register pool instance.

        Args:
            name: Pool name
            pool: Pool instance

        Raises:
            ValueError: If pool with given name already exists
        """
        if name in self._pools:
            raise ValueError(f"Pool already exists: {name}")
        self._pools[name] = pool
        logger.info("Registered pool: %s", name)

    def unregister(self, name: str) -> None:
        """Unregister pool instance.

        Args:
            name: Pool name
        """
        if name in self._pools:
            del self._pools[name]
            logger.info("Unregistered pool: %s", name)

    def get(self, name: str) -> Optional[Union[MongoPool, RedisPool]]:
        """Get pool by name.

        Args:
            name: Pool name

        Returns:
            Pool instance or None if not found
        """
        return self._pools.get(name)

    async def create_and_register(
        self, name: str, pool_type: str, **config: Any
    ) -> Union[MongoPool, RedisPool]:
        """Create and register pool instance.

        Args:
            name: Pool name
            pool_type: Pool type ("mongodb" or "redis")
            **config: Pool configuration

        Returns:
            Pool instance

        Raises:
            ValueError: If pool with given name already exists
            KeyError: If pool type is not registered
        """
        if name in self._pools:
            raise ValueError(f"Pool already exists: {name}")

        if pool_type == "mongodb":
            pool = await self._factory.create_mongo_pool(**config)
        elif pool_type == "redis":
            pool = await self._factory.create_redis_pool(**config)
        else:
            raise KeyError(f"Unknown pool type: {pool_type}")

        self.register(name, pool)
        return pool

    async def close_all(self) -> None:
        """Close all registered pools."""
        for name, pool in self._pools.items():
            try:
                await pool.close()
                logger.info("Closed pool: %s", name)
            except Exception:
                logger.exception("Failed to close pool: %s", name)
        self._pools.clear()
