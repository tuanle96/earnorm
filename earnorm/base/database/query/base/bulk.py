"""Base bulk operation classes.

This module provides base classes for bulk database operations.
It includes support for:
- Bulk inserts
- Bulk updates
- Bulk deletes
- Transaction integration

Examples:
    ```python
    class MongoBulkInsert(BulkOperation[AsyncIOMotorDatabase, Dict[str, Any]]):
        async def execute(self, session: Optional[ClientSession] = None) -> None:
            collection = self.db[self.collection]
            await collection.insert_many(self.documents, session=session)
    ```
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

DBType = TypeVar("DBType")
DocumentType = TypeVar("DocumentType")
SessionType = TypeVar("SessionType")


class BulkOperation(ABC, Generic[DBType, DocumentType, SessionType]):
    """Base class for bulk operations.

    This class provides common functionality for bulk database operations.
    It supports transaction integration and batch processing.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)
        DocumentType: Document type (e.g. Dict[str, Any])
        SessionType: Session type for transactions (e.g. ClientSession)

    Examples:
        ```python
        class MongoBulkInsert(BulkOperation[AsyncIOMotorDatabase, Dict[str, Any], ClientSession]):
            async def execute(self, session: Optional[ClientSession] = None) -> None:
                collection = self.db[self.collection]
                await collection.insert_many(self.documents, session=session)
        ```
    """

    def __init__(self, collection: str, documents: List[DocumentType]) -> None:
        """Initialize bulk operation.

        Args:
            collection: Collection/table name
            documents: Documents to process
        """
        self.collection = collection
        self.documents = documents
        self.batch_size = 1000

    @abstractmethod
    async def execute(self, session: Optional[SessionType] = None) -> None:
        """Execute bulk operation.

        This method should execute the bulk operation in batches.
        It should support transaction integration via session parameter.

        Args:
            session: Database session for transaction support

        Examples:
            ```python
            bulk = MongoBulkInsert("users", documents)
            async with transaction() as session:
                await bulk.execute(session)
            ```
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate bulk operation.

        This method should validate:
        - Collection name is valid
        - Documents are valid
        - Batch size is valid

        Raises:
            ValueError: If operation is invalid

        Examples:
            ```python
            bulk = MongoBulkInsert("users", documents)
            bulk.validate()  # Raises if invalid
            ```
        """
        pass

    def set_batch_size(self, size: int) -> None:
        """Set batch size for operation.

        Args:
            size: Batch size (must be positive)

        Raises:
            ValueError: If size is invalid

        Examples:
            ```python
            bulk = MongoBulkInsert("users", documents)
            bulk.set_batch_size(100)
            ```
        """
        if size <= 0:
            raise ValueError("Batch size must be positive")
        self.batch_size = size
