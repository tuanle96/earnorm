"""Database adapter interface.

This module provides the base interface for database adapters.
Each database type should implement this interface to handle type conversion.
"""

from typing import Any, Optional, Protocol, TypeVar

from earnorm.fields.types import DatabaseValue

T = TypeVar("T")  # Field value type


class DatabaseAdapter(Protocol[T]):
    """Protocol for database adapters.

    This protocol defines the interface that all database adapters must implement.
    Each database type (MongoDB, PostgreSQL, MySQL, etc.) should have its own adapter
    that implements this protocol.
    """

    @property
    def backend_name(self) -> str:
        """Get the name of the database backend.

        Returns:
            str: Database backend name (e.g. 'mongodb', 'postgres', 'mysql')
        """
        ...

    def get_field_type(self) -> str:
        """Get the database-specific field type.

        Returns:
            str: Field type in database (e.g. 'VARCHAR', 'INTEGER', etc.)
        """
        ...

    def get_field_options(self) -> dict[str, Any]:
        """Get database-specific field options.

        Returns:
            dict[str, Any]: Field options for the database
        """
        ...

    async def to_db_value(self, value: Optional[T]) -> DatabaseValue:
        """Convert Python value to database value.

        Args:
            value: Python value to convert

        Returns:
            DatabaseValue: Converted value for database
        """
        ...

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert database value to Python value.

        Args:
            value: Database value to convert

        Returns:
            Optional[T]: Converted Python value
        """
        ...


class BaseAdapter(DatabaseAdapter[T]):
    """Base implementation of database adapter.

    This class provides a base implementation that can be extended by
    specific database adapters.

    Attributes:
        field_type: Database field type
        field_options: Additional field options
    """

    def __init__(self, field_type: str, **field_options: Any) -> None:
        """Initialize adapter.

        Args:
            field_type: Database field type
            **field_options: Additional field options
        """
        self._field_type = field_type
        self._field_options = field_options

    @property
    def backend_name(self) -> str:
        """Get backend name.

        This should be overridden by subclasses.

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    def get_field_type(self) -> str:
        """Get field type.

        Returns:
            str: Database field type
        """
        return self._field_type

    def get_field_options(self) -> dict[str, Any]:
        """Get field options.

        Returns:
            dict[str, Any]: Field options
        """
        return self._field_options

    async def to_db_value(self, value: Optional[T]) -> DatabaseValue:
        """Convert to database value.

        This should be overridden by subclasses.

        Args:
            value: Value to convert

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert from database value.

        This should be overridden by subclasses.

        Args:
            value: Value to convert

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError
