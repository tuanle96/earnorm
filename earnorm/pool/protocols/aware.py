"""Pool aware protocol."""

from typing import Protocol, Union

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.pool import RedisPool


class PoolAware(Protocol):
    """Interface for components that need pool access.

    This protocol defines a standard interface for components that need to interact
    with a pool instance. By implementing this protocol, components can receive
    pool instances through dependency injection.

    Examples:
        ```python
        class CacheManager(PoolAware):
            async def set_pool(self, pool: RedisPool) -> None:
                self._pool = pool

            async def get(self, key: str) -> Any:
                async with self._pool.acquire() as conn:
                    return await conn.execute("get", key)
        ```
    """

    async def set_pool(self, pool: Union[MongoPool, RedisPool]) -> None:
        """Set pool instance.

        Args:
            pool: Pool instance to use
        """
        ...
