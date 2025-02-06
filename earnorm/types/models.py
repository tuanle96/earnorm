"""Model-related type definitions."""

from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Self,
    Union,
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

    _description: ClassVar[Optional[str]]
    """User-friendly description."""

    _table: ClassVar[Optional[str]]
    """Database table name."""

    _sequence: ClassVar[Optional[str]]
    """ID sequence name."""

    __fields__: ClassVar[Dict[str, BaseField]]
    """Model fields dictionary."""

    id: str
    """Record ID."""

    async def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
        ...

    @classmethod
    async def browse(cls, ids: Union[str, List[str]]) -> Self:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Recordset containing the records
        """
        ...

    @classmethod
    async def create(cls, values: Dict[str, Any]) -> Self:
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

    async def write(self, values: Dict[str, Any]) -> Self:
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

__all__ = ["ModelProtocol", "ModelName", "FieldName", "RecordID", "DatabaseModel"]
