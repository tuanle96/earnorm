"""Model-related type definitions."""

from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)

from earnorm.base.database.transaction.base import Transaction


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for all models.

    This protocol defines the interface that all models must implement.
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

    id: int
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
    async def browse(
        cls, ids: Union[int, List[int]]
    ) -> Union["ModelProtocol", List["ModelProtocol"]]:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Single record or list of records
        """
        ...

    @classmethod
    async def create(cls, values: Dict[str, Any]) -> "ModelProtocol":
        """Create a new record.

        Args:
            values: Field values

        Returns:
            Created record
        """
        ...

    async def write(self, values: Dict[str, Any]) -> "ModelProtocol":
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
    ) -> AsyncContextManager[Transaction["ModelProtocol"]]:
        """Get transaction context manager.

        Returns:
            Transaction context manager
        """
        ...


# Model identifier types
ModelName = str  # e.g. "res.partner"
FieldName = str  # e.g. "name"
RecordID = int  # Record ID type

# Type alias for database model
DatabaseModel = ModelProtocol  # Type alias for database-backed models

__all__ = ["ModelProtocol", "ModelName", "FieldName", "RecordID", "DatabaseModel"]
