"""Database protocol definitions.

This module defines protocols for database operations with async-first approach.
All database operations are async by default.

Examples:
    ```python
    class MyDatabase(AsyncDatabaseProtocol[MyDB, MyColl]):
        def get_database(self) -> MyDB:
            return self._client[self._database]

        def get_collection(self, name: str) -> MyColl:
            return self._client[self._database][name]
    ```
"""

from typing import Protocol, TypeVar

# Type variables for database and collection
DBType = TypeVar("DBType", covariant=True)
CollType = TypeVar("CollType", covariant=True)


class AsyncDatabaseProtocol(Protocol[DBType, CollType]):
    """Protocol for database operations.

    Type Parameters:
        DBType: The database type (e.g. AsyncIOMotorDatabase)
        CollType: The collection type (e.g. AsyncIOMotorCollection)
    """

    def get_database(self) -> DBType:
        """Get database instance.

        Returns:
            Database instance
        """
        ...

    def get_collection(self, name: str) -> CollType:
        """Get collection instance.

        Args:
            name: Collection name

        Returns:
            Collection instance
        """
        ...

    @property
    def db(self) -> DBType:
        """Get database instance."""
        ...

    @property
    def collection(self) -> CollType:
        """Get collection instance."""
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
