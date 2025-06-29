"""Model type definitions.

This module contains type definitions for models to avoid circular imports.
"""

from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    Protocol,
    Self,
    runtime_checkable,
)

from earnorm.base.database.transaction.base import Transaction

# Type aliases
ModelName = str
FieldName = str
RecordID = str

# Forward reference for BaseField
BaseField = Any


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for database models.

    This protocol defines the interface that all database models must implement.
    It provides methods for CRUD operations and database interaction.
    """

    _store: ClassVar[bool]
    """Whether model supports storage."""

    _name: ClassVar[str]
    """Technical name of the model."""

    _description: ClassVar[str | None]
    """User-friendly description."""

    _table: ClassVar[str | None]
    """Database table name."""

    _sequence: ClassVar[str | None]
    """ID sequence name."""

    __fields__: ClassVar[dict[str, BaseField]]
    """Model fields dictionary."""

    id: str
    """Record ID."""

    async def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    def from_dict(self, data: dict[str, Any]) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
        ...

    @classmethod
    async def browse(cls, ids: str | list[str]) -> Self:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Recordset containing the records
        """
        ...

    @classmethod
    async def create(cls, values: dict[str, Any]) -> Self:
        """Create a new record.

        Args:
            values: Field values

        Returns:
            Created record

        Examples:
            >>> user = await User.create({
            ...     "name": "John Doe",
            ...     "email": "john@example.com",
            ...     "age": 25,
            ...     "status": "active",
            ... })
            >>> print(user.name)  # John Doe
        """
        ...

    async def write(self, values: dict[str, Any]) -> Self:
        """Update record with values.

        Args:
            values: Field values to update

        Returns:
            Updated record
        """
        ...

    async def unlink(self) -> bool:
        """Delete record from database.

        Returns:
            True if record was deleted
        """
        ...

    async def with_transaction(
        self,
    ) -> AsyncContextManager[Transaction[Self]]:
        """Get transaction context manager.

        Returns:
            Transaction context manager
        """
        ...


# Type aliases
DatabaseModel = ModelProtocol  # Type alias for database-backed models

__all__ = ["DatabaseModel", "FieldName", "ModelName", "ModelProtocol", "RecordID"]
