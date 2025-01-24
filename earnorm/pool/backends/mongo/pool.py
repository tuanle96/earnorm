"""MongoDB connection pool implementation using motor driver.

This module provides a connection pool implementation for MongoDB using the motor driver.
It includes connection lifecycle management, retry mechanisms, and circuit breakers.

Example:
    Create a MongoDB pool with retry and circuit breaker:

    ```python
    from earnorm.pool.backends.mongo import MongoPool
    from earnorm.pool.retry import RetryPolicy
    from earnorm.pool.circuit import CircuitBreaker

    # Create retry policy with exponential backoff
    retry_policy = RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=0.1
    )

    # Create circuit breaker
    circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        reset_timeout=30.0,
        half_open_timeout=5.0
    )

    # Create pool
    pool = MongoPool(
        uri="mongodb://localhost:27017",
        database="test",
        collection="users",
        min_size=1,
        max_size=10,
        max_idle_time=300,
        max_lifetime=3600,
        retry_policy=retry_policy,
        circuit_breaker=circuit_breaker
    )

    # Use pool with context manager
    async with pool.connection() as conn:
        # Execute find operation
        user = await conn.execute_typed(
            "find_one",
            filter={"username": "john"}
        )
    ```
"""

import asyncio
from typing import Any, Coroutine, Dict, List, Optional, TypeVar, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.pool.backends.base.pool import BasePool
from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.circuit import CircuitBreaker
from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.errors import PoolError
from earnorm.pool.retry import RetryPolicy

DBType = TypeVar("DBType", bound=AsyncIOMotorDatabase[Dict[str, Any]])
CollType = TypeVar("CollType", bound=AsyncIOMotorCollection[Dict[str, Any]])


def wrap_none() -> Coroutine[Any, Any, None]:
    """Helper function to wrap None in a coroutine."""

    async def _wrapped() -> None:
        pass

    return _wrapped()


class NestedCoroutine:
    """Helper class for nested coroutines."""

    @staticmethod
    def wrap_none() -> Coroutine[Any, Any, Coroutine[Any, Any, None]]:
        async def _outer() -> Coroutine[Any, Any, None]:
            async def _inner() -> None:
                return None

            return _inner()

        return _outer()


class MongoPool(BasePool[DBType, CollType]):
    """MongoDB connection pool implementation.

    Examples:
        >>> pool = MongoPool(
        ...     uri="mongodb://localhost:27017",
        ...     database="test",
        ...     min_size=5,
        ...     max_size=20
        ... )
        >>> await pool.init()
        >>> conn = await pool.acquire()
        >>> await conn.execute_typed("find_one", "users", {"name": "John"})
        {"_id": "...", "name": "John", "age": 30}
        >>> await pool.release(conn)
        >>> await pool.close()
    """

    def __init__(
        self,
        uri: str,
        database: str,
        collection: str = "default",
        min_size: int = 1,
        max_size: int = 10,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        """Initialize MongoDB pool.

        Args:
            uri: MongoDB connection URI
            database: Database name
            collection: Collection name
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum connection idle time in seconds
            max_lifetime: Maximum connection lifetime in seconds
            retry_policy: Retry policy for operations
            circuit_breaker: Circuit breaker for operations
        """
        super().__init__(
            uri=uri,
            database=database,
            min_size=min_size,
            max_size=max_size,
            max_idle_time=max_idle_time,
            max_lifetime=max_lifetime,
        )
        self._collection = collection
        self._client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None
        self._connections: List[MongoConnection[DBType, CollType]] = []
        self._lock = asyncio.Lock()

    async def _create_client(self) -> AsyncIOMotorClient[Dict[str, Any]]:
        """Create MongoDB client.

        Returns:
            AsyncIOMotorClient: MongoDB client instance

        Raises:
            PoolError: If client creation fails
        """
        try:
            return AsyncIOMotorClient(self._uri)
        except Exception as e:
            raise PoolError(f"Failed to create MongoDB client: {str(e)}") from e

    def _create_connection(self) -> ConnectionProtocol[DBType, CollType]:
        """Create new connection.

        Returns:
            New connection instance

        Raises:
            PoolError: If connection creation fails
        """
        try:
            if not self._client:
                self._client = AsyncIOMotorClient(
                    self._uri,
                    serverSelectionTimeoutMS=int(self._connection_timeout * 1000),
                )
            return cast(
                ConnectionProtocol[DBType, CollType],
                MongoConnection(
                    client=self._client,
                    database=self._database or "",
                    collection=self._collection,
                    max_idle_time=self._max_idle_time,
                    max_lifetime=self._max_lifetime,
                ),
            )
        except Exception as e:
            raise PoolError(f"Failed to create connection: {str(e)}") from e

    async def init(self) -> None:
        """Initialize pool.

        Raises:
            PoolError: If initialization fails
        """
        try:
            if not self._client:
                self._client = await self._create_client()
            await self._init_pool()
        except Exception as e:
            raise PoolError(f"Failed to initialize pool: {str(e)}") from e

    async def _init_pool(self) -> None:
        """Initialize pool with minimum connections.

        Raises:
            PoolError: If pool initialization fails
        """
        for _ in range(self.min_size):
            conn = self._create_connection()
            self._connections.append(cast(MongoConnection[DBType, CollType], conn))

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close pool.

        Raises:
            PoolError: If close fails
        """
        try:
            if self._client:
                self._client.close()
                self._client = None
            await self.clear()
            return await super().close()
        except Exception as e:
            raise PoolError(f"Failed to close pool: {str(e)}") from e

    async def acquire(
        self,
    ) -> Coroutine[Any, Any, ConnectionProtocol[DBType, CollType]]:
        """Acquire connection from pool.

        Returns:
            Connection from pool

        Raises:
            PoolError: If acquire fails
        """
        try:
            return await super().acquire()
        except Exception as e:
            raise PoolError(f"Failed to acquire connection: {str(e)}") from e

    async def release(
        self, connection: ConnectionProtocol[DBType, CollType]
    ) -> Coroutine[Any, Any, None]:
        """Release connection back to pool.

        Args:
            connection: Connection to release

        Raises:
            PoolError: If release fails
        """
        try:
            if not isinstance(connection, MongoConnection):
                raise PoolError("Invalid connection type")
            return await super().release(connection)
        except Exception as e:
            raise PoolError(f"Failed to release connection: {str(e)}") from e

    async def health_check(self) -> Coroutine[Any, Any, bool]:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        try:
            if not self._client:

                async def _health_check() -> bool:
                    return False

                return _health_check()  # type: ignore

            # Check MongoDB server health
            await self._client.admin.command("ping")
            return await super().health_check()
        except Exception:

            async def _health_check() -> bool:
                return False

            return _health_check()  # type: ignore

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dict[str, Any]: Pool statistics
        """
        return {
            "size": self.size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": self.available,
            "in_use": self.in_use,
        }
