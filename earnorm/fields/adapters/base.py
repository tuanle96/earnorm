"""Database adapter interface.

This module provides the base interface for database adapters.
Each database type should implement this interface to handle type conversion.

Examples:
    >>> class PostgresAdapter(BaseAdapter[str]):
    ...     @property
    ...     def backend_name(self) -> str:
    ...         return "postgres"
    ...
    ...     async def to_db_value(self, value: Optional[str]) -> DatabaseValue:
    ...         if value is None:
    ...             return None
    ...         return str(value)
    ...
    ...     async def from_db_value(self, value: DatabaseValue) -> Optional[str]:
    ...         if value is None:
    ...             return None
    ...         return str(value)
"""

from typing import Any, Generic, Optional, Protocol, TypeVar

from earnorm.types.fields import DatabaseValue

# Type variable for field value type
T = TypeVar("T")


class DatabaseAdapter(Protocol[T]):
    """Protocol for database adapters.

    This protocol defines the interface that all database adapters must implement.
    Each database type (MongoDB, PostgreSQL, MySQL, etc.) should have its own adapter
    that implements this protocol.

    Type Parameters:
        T: Field value type
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

        Raises:
            FieldValidationError: If value cannot be converted
        """
        ...

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert database value to Python value.

        Args:
            value: Database value to convert

        Returns:
            Optional[T]: Converted Python value

        Raises:
            FieldValidationError: If value cannot be converted
        """
        ...


class BaseAdapter(DatabaseAdapter[T], Generic[T]):
    """Base implementation of database adapter.

    This class provides a base implementation that can be extended by
    specific database adapters.

    Type Parameters:
        T: Field value type

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
        self._field_type: str = field_type
        self._field_options: dict[str, Any] = field_options

    @property
    def backend_name(self) -> str:
        """Get backend name.

        This should be overridden by subclasses.

        Returns:
            str: Database backend name

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError("Subclasses must implement backend_name")

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

        Returns:
            DatabaseValue: Converted database value

        Raises:
            NotImplementedError: If not overridden
            FieldValidationError: If value cannot be converted
        """
        raise NotImplementedError("Subclasses must implement to_db_value()")

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert from database value.

        This should be overridden by subclasses.

        Args:
            value: Value to convert

        Returns:
            Optional[T]: Converted Python value

        Raises:
            NotImplementedError: If not overridden
            FieldValidationError: If value cannot be converted
        """
        raise NotImplementedError("Subclasses must implement from_db_value()")

    def _validate_value(self, value: Any) -> None:
        """Validate value before conversion.

        This method can be overridden by subclasses to add custom validation.

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        pass

    def _prepare_value(self, value: Any) -> Any:
        """Prepare value for conversion.

        This method can be overridden by subclasses to add custom preparation.

        Args:
            value: Value to prepare

        Returns:
            Any: Prepared value
        """
        return value
