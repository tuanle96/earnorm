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

    async def _prefetch_records(self, fields: List[str]) -> None:
        """Prefetch records efficiently using cache.

        This method loads the specified fields for all records in the current recordset
        in a single batch operation. It uses cache when available and loads from
        database only for uncached values.

        Args:
            fields: List of field names to prefetch
        """
        ...

    async def optimize_memory(self, max_records: int = 1000) -> None:
        """Optimize memory usage by clearing cache if needed.

        This method helps manage memory usage by clearing cache for recordsets
        that exceed a certain size threshold. It is useful for large recordsets
        where keeping all records in cache may consume too much memory.

        Args:
            max_records: Maximum number of records to keep in cache
        """
        ...

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for current recordset.

        This method returns statistics about the cache usage for the current recordset,
        including:
        - Total number of records
        - Number of cached fields per record
        - Total memory usage estimate

        Returns:
            Dict containing cache stats:
            - total_records: Total number of records in recordset
            - cached_fields: Dict mapping record ID to number of cached fields
            - memory_usage: Rough estimate of memory usage in bytes
        """
        ...

    def mark_for_prefetch(self, fields: List[str]) -> None:
        """Mark fields for prefetching.

        This method marks fields to be prefetched later when execute_prefetch is called.
        It is useful when you want to batch multiple prefetch operations together
        for better performance.

        Args:
            fields: List of field names to prefetch
        """
        ...

    async def execute_prefetch(self) -> None:
        """Execute all pending prefetch operations.

        This method executes all prefetch operations that were previously marked
        using mark_for_prefetch. It batches multiple prefetch operations together
        for better performance.
        """
        ...


# Type aliases
DatabaseModel = ModelProtocol  # Type alias for database-backed models

__all__ = ["ModelProtocol", "ModelName", "FieldName", "RecordID", "DatabaseModel"]
