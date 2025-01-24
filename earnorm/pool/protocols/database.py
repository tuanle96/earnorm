"""Database protocol definitions.

This module defines protocols for database operations, including type-safe
database and collection access.

Examples:
    ```python
    class MyDatabase(DatabaseProtocol[MyDB, MyColl]):
        def get_database(self) -> MyDB:
            return self._db

        def get_collection(self, name: str) -> MyColl:
            return self._db[name]
    ```
"""

from typing import Any, Dict, Protocol, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from redis.asyncio import Redis

# Type variables for database and collection types
# These are covariant because they only appear in return position
DBType = TypeVar("DBType", covariant=True)
CollType = TypeVar("CollType", covariant=True)


class DatabaseProtocol(Protocol[DBType, CollType]):
    """Protocol for database operations.

    Type Parameters:
        DBType: The database type (e.g. AsyncIOMotorDatabase)
        CollType: The collection type (e.g. AsyncIOMotorCollection)
    """

    def get_database(self) -> DBType:
        """Get database instance.

        Returns:
            Database instance of type DBType
        """
        ...

    def get_collection(self, name: str) -> CollType:
        """Get collection by name.

        Args:
            name: Collection name

        Returns:
            Collection instance of type CollType
        """
        ...


class DatabaseAware(Protocol):
    """Protocol for objects that are aware of their database context."""

    @property
    def database_name(self) -> str:
        """Get database name.

        Returns:
            Database name
        """
        ...

    @property
    def collection_name(self) -> str:
        """Get collection name.

        Returns:
            Collection name
        """
        ...


# Concrete protocols for specific databases
class MongoDBProtocol(
    DatabaseProtocol[
        AsyncIOMotorDatabase[Dict[str, Any]], AsyncIOMotorCollection[Dict[str, Any]]
    ]
):
    """Protocol for MongoDB operations."""

    pass


class RedisDBProtocol(DatabaseProtocol[Redis, Redis]):
    """Protocol for Redis operations.

    Note: Redis doesn't have separate database/collection concepts,
    so we use Redis client for both.
    """

    pass
