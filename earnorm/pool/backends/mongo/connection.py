"""MongoDB connection implementation using motor driver.

This module provides a connection implementation for MongoDB using the motor driver.
It includes connection lifecycle management and operation execution.

Example:
    Create a MongoDB connection:

    ```python
    from motor.motor_asyncio import AsyncIOMotorClient
    from earnorm.pool.backends.mongo import MongoConnection

    # Create client
    client = AsyncIOMotorClient("mongodb://localhost:27017")

    # Create connection
    conn = MongoConnection(
        client=client,
        database="test",
        collection="users",
        max_idle_time=300,
        max_lifetime=3600
    )

    # Use connection
    db = await conn.get_database()
    users = await conn.get_collection("users")

    # Execute operations
    user = await conn.execute_typed(
        "find_one",
        collection=users,
        filter={"username": "john"}
    )
    ```
"""

import time
from typing import Any, Coroutine, Dict, Optional, TypeVar, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.pool.decorators import with_resilience
from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.errors import ConnectionError, OperationError

DBType = TypeVar("DBType", bound=AsyncIOMotorDatabase[Dict[str, Any]])
CollType = TypeVar("CollType", bound=AsyncIOMotorCollection[Dict[str, Any]])


def wrap_coroutine(value: Any) -> Coroutine[Any, Any, Any]:
    """Helper function to wrap a value in a coroutine."""

    async def _wrapped() -> Any:
        return value

    return _wrapped()


class MongoConnection(ConnectionProtocol[DBType, CollType]):
    """MongoDB connection implementation.

    Examples:
        >>> conn = MongoConnection(client, "test_db", "test_collection")
        >>> await conn.ping()
        True
        >>> await conn.close()
        >>> await conn.execute_typed("find_one", {"_id": "123"})
        {"_id": "123", "name": "test"}
    """

    def __init__(
        self,
        client: AsyncIOMotorClient[Dict[str, Any]],
        database: str,
        collection: str,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
    ) -> None:
        """Initialize MongoDB connection.

        Args:
            client: Motor client instance
            database: Database name
            collection: Collection name
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
        """
        self._client = client
        self._database = database
        self._collection = collection
        self._db: Optional[DBType] = None
        self._coll: Optional[CollType] = None
        self._created_at = time.time()
        self._last_used_at = time.time()
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime

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

    def get_database(self) -> DBType:
        """Get database instance.

        Returns:
            DBType: MongoDB database instance

        Raises:
            ConnectionError: If database access fails
        """
        if self._db is None:
            try:
                db = self._client[self._database]
                self._db = cast(DBType, db)
            except Exception as e:
                raise ConnectionError(f"Failed to get database: {str(e)}") from e
        return self._db

    def get_collection(self, name: str) -> CollType:
        """Get collection instance.

        Args:
            name: Collection name

        Returns:
            CollType: MongoDB collection instance

        Raises:
            ConnectionError: If collection access fails
        """
        try:
            db = self.get_database()
            coll = db[name]
            return cast(CollType, coll)
        except Exception as e:
            raise ConnectionError(f"Failed to get collection: {str(e)}") from e

    @property
    def db(self) -> DBType:
        """Get database instance."""
        return self.get_database()

    @property
    def collection(self) -> CollType:
        """Get collection instance."""
        if self._coll is None:
            self._coll = self.get_collection(self._collection)
        return self._coll

    @with_resilience()
    async def _ping_impl(self) -> bool:
        """Internal ping implementation."""
        try:
            await self.db.command("ping")
            self.touch()
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to ping database: {str(e)}") from e

    async def ping(self) -> Coroutine[Any, Any, bool]:
        """Ping database to check connection.

        Returns:
            True if ping successful

        Raises:
            ConnectionError: If ping fails
        """

        async def _ping() -> bool:
            return await self._ping_impl()

        return _ping()

    @with_resilience()
    async def _execute_impl(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Internal execute implementation."""
        try:
            result = await getattr(self.collection, operation)(*args, **kwargs)
            self.touch()
            return result
        except Exception as e:
            raise OperationError(
                f"Failed to execute operation {operation}: {str(e)}"
            ) from e

    async def execute_typed(
        self, operation: str, *args: Any, **kwargs: Any
    ) -> Coroutine[Any, Any, Any]:
        """Execute typed operation.

        Args:
            operation: Operation name
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Any: Operation result

        Raises:
            OperationError: If operation fails
        """

        async def _execute() -> Any:
            return await self._execute_impl(operation, *args, **kwargs)

        return _execute()

    async def _close_impl(self) -> None:
        """Internal close implementation."""
        try:
            if self._client:
                self._client.close()
                self._db = None
                self._coll = None
        except Exception as e:
            raise ConnectionError(f"Failed to close connection: {str(e)}") from e

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close connection.

        Raises:
            ConnectionError: If close fails
        """

        async def _close() -> None:
            await self._close_impl()

        return _close()
