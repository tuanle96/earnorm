"""Database-related type definitions."""

from typing import (
    Any,
    AsyncContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)


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

    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
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

    async def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
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
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows.

        Args:
            query: Query string
            params: Query parameters

        Returns:
            List of rows

        Raises:
            DatabaseError: If query execution fails
        """
        ...

    async def fetch_value(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
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


__all__ = ["DatabaseProtocol"]
