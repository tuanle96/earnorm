"""Pool context implementation."""

from types import TracebackType
from typing import Any, Optional, Type, Union

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.pool import RedisPool


class PoolContext:
    """Context for managing pool lifecycle.

    This context manager ensures that pools are properly initialized and cleaned up.
    It provides a safe way to use pools in async with statements.

    Examples:
        ```python
        # Create pool
        pool = MongoPool(
            uri="mongodb://localhost:27017",
            database="test"
        )

        # Use pool in context
        async with PoolContext(pool) as p:
            conn = await p.acquire()
            try:
                await conn.execute(...)
            finally:
                await p.release(conn)

        # Pool is automatically closed after context
        ```
    """

    def __init__(self, pool: Union[MongoPool, RedisPool]) -> None:
        """Initialize pool context.

        Args:
            pool: Pool instance to manage
        """
        self.pool = pool

    async def __aenter__(self) -> Union[MongoPool, RedisPool]:
        """Initialize pool on context enter.

        Returns:
            Pool instance
        """
        await self.pool.init()
        return self.pool

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Close pool on context exit."""
        await self.pool.close()


class ConnectionContext:
    """Context for managing connection lifecycle.

    This context manager ensures that connections are properly acquired and released.
    It provides a safe way to use connections in async with statements.

    Examples:
        ```python
        # Create pool
        pool = MongoPool(
            uri="mongodb://localhost:27017",
            database="test"
        )

        # Use connection in context
        async with ConnectionContext(pool) as conn:
            await conn.execute(...)

        # Connection is automatically released after context
        ```
    """

    def __init__(self, pool: Union[MongoPool, RedisPool]) -> None:
        """Initialize connection context.

        Args:
            pool: Pool instance to get connection from
        """
        self.pool = pool
        self.conn: Any = None

    async def __aenter__(self) -> Any:
        """Acquire connection on context enter.

        Returns:
            Connection instance
        """
        self.conn = await self.pool.acquire()
        return self.conn

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Release connection on context exit."""
        await self.pool.release(self.conn)
