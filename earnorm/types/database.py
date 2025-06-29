"""Database-related type definitions."""

from typing import (
    Any,
    AsyncContextManager,
    Protocol,
    runtime_checkable,
)

from .models import ModelProtocol as DatabaseModel, RecordID


@runtime_checkable
class DatabaseProtocol(Protocol):
    """Protocol for database adapters.

    This protocol defines the interface that all database adapters must implement.
    It provides methods for database operations and connection management.
    """

    async def connect(self) -> None:
        """Connect to database.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from database.

        Raises:
            DatabaseConnectionError: If disconnection fails
        """
        ...

    async def begin(self) -> AsyncContextManager[Any]:
        """Begin transaction.

        Returns:
            Transaction context manager

        Raises:
            DatabaseError: If transaction fails
        """
        ...

    async def commit(self) -> None:
        """Commit transaction.

        Raises:
            DatabaseError: If commit fails
        """
        ...

    async def rollback(self) -> None:
        """Rollback transaction.

        Raises:
            DatabaseError: If rollback fails
        """
        ...

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute query.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            Query result

        Raises:
            DatabaseError: If query execution fails
        """
        ...

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Fetch single row.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            Single row or None if not found

        Raises:
            DatabaseError: If query execution fails
        """
        ...

    async def fetch_all(
        self,
        collection: str,
        ids: list[str],
        fields: list[str],
    ) -> list[dict[str, Any]]:
        """Fetch multiple records by IDs.

        Args:
            collection: Collection/table name
            ids: List of record IDs to fetch
            fields: List of fields to fetch

        Returns:
            List of records

        Raises:
            DatabaseError: If fetch fails
        """
        ...

    async def fetch_value(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Fetch single value.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            Single value or None if not found

        Raises:
            DatabaseError: If query execution fails
        """
        ...

    async def create(self, model: DatabaseModel, values: dict[str, Any]) -> RecordID:
        """Create a new record.

        Args:
            model: Model instance
            values: Field values

        Returns:
            Created record ID

        Raises:
            DatabaseError: If creation fails
        """
        ...


__all__ = ["DatabaseProtocol"]
