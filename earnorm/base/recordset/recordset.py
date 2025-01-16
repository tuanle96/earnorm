"""RecordSet implementation."""

from __future__ import annotations

from typing import (
    Any,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.query.builder import QueryBuilder
from earnorm.base.types import ContainerProtocol, DocumentType
from earnorm.di import container

T = TypeVar("T", bound=ModelInterface)


class RecordSet(Generic[T]):
    """Record set implementation.

    This class provides a fluent interface for querying models:
    - Filtering
    - Sorting
    - Pagination
    - Projection

    It uses method chaining to build queries and executes them lazily.

    Attributes:
        _model_cls: Model class
        _records: List of records
        _query: Query builder
    """

    def __init__(self, model_cls: Type[T], records: List[T]) -> None:
        """Initialize record set.

        Args:
            model_cls: Model class
            records: Initial records
        """
        self._model_cls = model_cls
        self._records = records
        self._query = QueryBuilder()

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[T]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union[T, Sequence[T]]:
        """Get item by index.

        Args:
            index: Integer index or slice

        Returns:
            Single record or sequence of records
        """
        return self._records[index]

    def __len__(self) -> int:
        """Get length.

        Returns:
            Number of records
        """
        return len(self._records)

    def filter(self, **kwargs: Any) -> RecordSet[T]:
        """Filter records.

        Args:
            **kwargs: Filter conditions

        Returns:
            Self for chaining
        """
        self._query.filter(**kwargs)
        return self

    def filter_by_id(self, id: str) -> RecordSet[T]:
        """Filter by ID.

        Args:
            id: Record ID

        Returns:
            Self for chaining
        """
        self._query.filter_by_id(id)
        return self

    def sort(self, field: str, direction: int = 1) -> RecordSet[T]:
        """Sort records.

        Args:
            field: Field to sort by
            direction: Sort direction (1 for ascending, -1 for descending)

        Returns:
            Self for chaining
        """
        self._query.sort(field, direction)
        return self

    def limit(self, limit: int) -> RecordSet[T]:
        """Limit records.

        Args:
            limit: Maximum number of records

        Returns:
            Self for chaining
        """
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> RecordSet[T]:
        """Offset records.

        Args:
            offset: Number of records to skip

        Returns:
            Self for chaining
        """
        self._query.offset(offset)
        return self

    def project(self, *fields: str, exclude: bool = False) -> RecordSet[T]:
        """Project fields.

        Args:
            *fields: Fields to include/exclude
            exclude: Whether to exclude fields instead of including

        Returns:
            Self for chaining
        """
        self._query.project(*fields, exclude=exclude)
        return self

    async def all(self) -> List[T]:
        """Get all records.

        Returns:
            List of records matching the query
        """
        query = self._query.build()

        # Get collection
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[
            cast(str, getattr(self._model_cls, "collection", ""))
        ]

        # Execute query
        cursor = collection.find(
            filter=query["filter"],
            sort=query.get("sort"),
        )
        documents: List[DocumentType] = cast(
            List[DocumentType], await cursor.to_list(length=None)  # type: ignore
        )

        # Convert to models
        return [self._model_cls(**doc) for doc in documents]  # type: ignore

    async def first(self) -> Optional[T]:
        """Get first record.

        Returns:
            First record or None if no records found
        """
        self._query.limit(1)
        records = await self.all()
        return records[0] if records else None

    async def count(self) -> int:
        """Count records.

        Returns:
            Number of records matching the query
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db

        # Get collection
        collection: AsyncIOMotorCollection[DocumentType] = db[
            cast(str, getattr(self._model_cls, "collection", ""))
        ]

        # Count documents
        return await collection.count_documents(self._query.build()["filter"])

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            String representation of the record set
        """
        return f"RecordSet({self._model_cls.__name__}, {str(self._query)})"
