"""MongoDB connection implementation."""

from typing import Any, Dict, Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.pool.core.connection import BaseConnection


class MongoConnection(BaseConnection):
    """MongoDB connection implementation."""

    def __init__(
        self, client: AsyncIOMotorClient[Dict[str, Any]], database: str, **config: Any
    ) -> None:
        """Initialize MongoDB connection.

        Args:
            client: Motor client instance
            database: Database name
            **config: Additional configuration

        Examples:
            >>> from motor.motor_asyncio import AsyncIOMotorClient
            >>> client = AsyncIOMotorClient("mongodb://localhost:27017")
            >>> conn = MongoConnection(client, "test")
            >>> await conn.ping()
            True
            >>> await conn.execute("find_one", "users", {"name": "John"})
            {"_id": "...", "name": "John", "age": 30}
        """
        super().__init__()
        self._client = client
        self._database = database
        self._db: Optional[AsyncIOMotorDatabase[Dict[str, Any]]] = None

    @property
    def database(self) -> AsyncIOMotorDatabase[Dict[str, Any]]:
        """Get database instance."""
        if self._db is None:
            self._db = self._client[self._database]
        return self._db

    async def ping(self) -> bool:
        """Check connection health.

        Returns:
            True if connection is healthy
        """
        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close connection."""
        await super().close()
        self._client.close()

    async def execute(
        self, operation: str, collection: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute MongoDB operation.

        Args:
            operation: Operation name (e.g. find_one, insert_one)
            collection: Collection name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Examples:
            >>> # Find one document
            >>> await conn.execute("find_one", "users", {"name": "John"})
            {"_id": "...", "name": "John", "age": 30}

            >>> # Insert one document
            >>> await conn.execute(
            ...     "insert_one",
            ...     "users",
            ...     {"name": "John", "age": 30}
            ... )
            InsertOneResult(...)

            >>> # Update many documents
            >>> await conn.execute(
            ...     "update_many",
            ...     "users",
            ...     {"age": {"$lt": 18}},
            ...     {"$set": {"is_adult": False}}
            ... )
            UpdateResult(...)
        """
        self.touch()
        coll: AsyncIOMotorCollection[Dict[str, Any]] = self.database[collection]
        method = getattr(coll, operation)
        return await method(*args, **kwargs)
