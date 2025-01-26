"""MongoDB connection implementation.

This module provides MongoDB connection functionality.
It handles connection lifecycle, operation execution, and error handling.

Examples:
    ```python
    connection = MongoConnection(
        host="localhost",
        port=27017,
        database="test",
    )
    await connection.connect()
    result = await conn.execute("find_one", {"_id": "123"})
    await connection.disconnect()
    ```
"""

import time
from typing import Any, TypeVar, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

# pylint: disable=redefined-builtin
from earnorm.exceptions import ConnectionError, QueryError
from earnorm.pool.constants import DEFAULT_MAX_IDLE_TIME, DEFAULT_MAX_LIFETIME
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.decorators import with_resilience
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol

DBType = TypeVar("DBType", bound=AsyncIOMotorDatabase[dict[str, Any]])
CollType = TypeVar("CollType", bound=AsyncIOMotorCollection[dict[str, Any]])


class MongoConnection(AsyncConnectionProtocol[DBType, CollType]):
    """MongoDB connection implementation."""

    def __init__(
        self,
        client: AsyncIOMotorClient[dict[str, Any]],
        database: str,
        collection: str,
        max_idle_time: int = DEFAULT_MAX_IDLE_TIME,
        max_lifetime: int = DEFAULT_MAX_LIFETIME,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize MongoDB connection.

        Args:
            client: MongoDB client
            database: Database name
            collection: Collection name
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
        """
        self._client = client
        self._database = database
        self._collection = collection
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker

        self._created_at = time.time()
        self._last_used_at = time.time()

    @property
    def backend(self) -> str:
        """Get backend name.

        Returns:
            str: Backend name
        """
        return "mongodb"

    @property
    def created_at(self) -> float:
        """Get connection creation timestamp."""
        return self._created_at

    @property
    def last_used_at(self) -> float:
        """Get last usage timestamp."""
        return self._last_used_at

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self._last_used_at

    @property
    def lifetime(self) -> float:
        """Get lifetime in seconds."""
        return time.time() - self._created_at

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        return (
            self.idle_time > self._max_idle_time or self.lifetime > self._max_lifetime
        )

    def touch(self) -> None:
        """Update last used timestamp."""
        self._last_used_at = time.time()

    @with_resilience(backend="mongodb")
    async def _ping_impl(self) -> bool:
        """Internal ping implementation."""
        try:
            await self._client.admin.command("ping")
            self.touch()
            return True
        except Exception as e:
            raise ConnectionError(
                f"Failed to ping MongoDB: {e!s}",
                backend=self.backend,
            ) from e

    async def ping(self) -> bool:
        """Check connection health."""
        return await self._ping_impl()

    async def close(self) -> None:
        """Close connection."""
        self._client.close()

    @with_resilience(backend="mongodb")
    async def _execute_impl(self, operation: str, **kwargs: Any) -> Any:
        """Internal execute implementation."""
        try:
            self.touch()
            collection = self.collection
            method = getattr(collection, operation)
            result = await method(**kwargs)
            return result
        except Exception as e:
            raise QueryError(
                f"Failed to execute operation {operation}: {e!s}",
                backend=self.backend,
                query=operation,
            ) from e

    async def execute(self, operation: str, **kwargs: Any) -> Any:
        """Execute MongoDB operation.

        Args:
            operation: Operation name
            **kwargs: Operation arguments

        Returns:
            Operation result

        Raises:
            QueryError: If operation fails
        """
        return await self._execute_impl(operation, **kwargs)

    def get_database(self) -> DBType:
        """Get database instance."""
        return cast(DBType, self._client[self._database])

    def get_collection(self, name: str) -> CollType:
        """Get collection instance."""
        return cast(CollType, self.get_database()[name])

    @property
    def db(self) -> DBType:
        """Get database instance."""
        return self.get_database()

    @property
    def collection(self) -> CollType:
        """Get collection instance."""
        return self.get_collection(self._collection)

    async def connect(self) -> None:
        """Connect to MongoDB.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            await self.ping()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to MongoDB: {e!s}",
                backend=self.backend,
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        await self.close()
