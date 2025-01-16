"""RecordSet implementation."""

from __future__ import annotations

from typing import (
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.query.builder import QueryBuilder
from earnorm.base.types import ContainerProtocol, DocumentType, ModelProtocol
from earnorm.di import container

T = TypeVar("T", bound=ModelProtocol)


class RecordSetError(Exception):
    """Base exception for RecordSet errors."""

    pass


class NoRecordError(RecordSetError):
    """Raised when no record is found but one is required."""

    pass


class MultipleRecordsError(RecordSetError):
    """Raised when multiple records are found but only one is expected."""

    pass


class RecordSet(Generic[T]):
    """Record set implementation.

    This class provides a fluent interface for querying models:
    - Filtering
    - Sorting
    - Pagination
    - Projection

    It uses method chaining to build queries and executes them lazily.
    When accessing attributes, it delegates to the first record in the set.

    Type Parameters:
        T: Type of model this record set handles

    Attributes:
        _model_cls: Model class
        _records: List of records
        _query: Query builder
    """

    def __init__(self, model_cls: Type[T], records: Optional[List[T]] = None) -> None:
        """Initialize record set.

        Args:
            model_cls: Model class
            records: Initial records, defaults to empty list if None

        Raises:
            TypeError: If model_cls does not implement ModelProtocol
        """
        # Check if model_cls implements required attributes and methods
        required_attrs = [
            "_name",
            "_collection",
            "_abstract",
            "_data",
            "_indexes",
            "__annotations__",
            "get_collection_name",
        ]
        for attr in required_attrs:
            if not hasattr(model_cls, attr):
                raise TypeError(f"model_cls must have {attr} attribute/method")

        self._model_cls = model_cls
        self._records = records if records is not None else []
        self._query = QueryBuilder()

    def __getattr__(self, name: str) -> Any:
        """Get attribute from first record.

        This method is called when an attribute is not found in the RecordSet.
        It delegates the attribute lookup to the first record in the set.

        Args:
            name: Name of the attribute

        Returns:
            Attribute value from the first record

        Raises:
            AttributeError: If no records exist or attribute not found
            IndexError: If no records exist

        Examples:
            >>> user = User(name="admin")  # Returns RecordSet
            >>> print(user.name)  # Accesses name from first record
        """
        if not self._records:
            raise AttributeError("Cannot access attributes of empty RecordSet")
        return getattr(self._records[0], name)

    @classmethod
    async def create(cls, model_cls: Type[T], **kwargs: Any) -> RecordSet[T]:
        """Create a new record.

        Args:
            model_cls: Model class
            **kwargs: Model data

        Returns:
            RecordSet containing the new record

        Examples:
            >>> user = await RecordSet.create(User, name="admin")
            >>> await user.save()
        """
        instance = model_cls(**kwargs)
        await instance.save()  # type: ignore
        return cls(model_cls, [instance])

    async def exists(self) -> bool:
        """Check if any records exist.

        Returns:
            True if at least one record exists, False otherwise

        Examples:
            >>> users = User.search([["active", "=", True]])
            >>> if await users.exists():
            ...     print("Active users found")
        """
        query = self._query.build()
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[
            self._model_cls.get_collection_name()
        ]

        count = await collection.count_documents(query["filter"], limit=1)  # type: ignore
        return count > 0

    async def ensure_one(self) -> None:
        """Ensure exactly one record exists.

        Raises:
            NoRecordError: If no records exist
            MultipleRecordsError: If multiple records exist

        Examples:
            >>> try:
            ...     await users.ensure_one()  # Raises if not exactly one record
            ... except NoRecordError:
            ...     print("No user found")
            ... except MultipleRecordsError:
            ...     print("Multiple users found")
        """
        records = await self.all()
        if not records:
            raise NoRecordError("No record found")
        if len(records) > 1:
            raise MultipleRecordsError("Multiple records found")

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

        Raises:
            IndexError: If index is out of range
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

        Raises:
            ValueError: If filter conditions are invalid
        """
        self._query.filter(**kwargs)
        return self

    def filter_by_id(self, id: str) -> RecordSet[T]:
        """Filter by ID.

        Args:
            id: Record ID

        Returns:
            Self for chaining

        Raises:
            ValueError: If ID is invalid
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

        Raises:
            ValueError: If field or direction is invalid
        """
        if direction not in (-1, 1):
            raise ValueError("Sort direction must be 1 or -1")
        self._query.sort(field, direction)
        return self

    def limit(self, limit: int) -> RecordSet[T]:
        """Limit records.

        Args:
            limit: Maximum number of records

        Returns:
            Self for chaining

        Raises:
            ValueError: If limit is not a positive integer
        """
        if limit < 0:
            raise ValueError("Limit must be a positive integer")
        self._query.limit(limit)
        return self

    def offset(self, offset: int) -> RecordSet[T]:
        """Offset records.

        Args:
            offset: Number of records to skip

        Returns:
            Self for chaining

        Raises:
            ValueError: If offset is not a positive integer
        """
        if offset < 0:
            raise ValueError("Offset must be a positive integer")
        self._query.offset(offset)
        return self

    def project(self, *fields: str, exclude: bool = False) -> RecordSet[T]:
        """Project fields.

        Args:
            *fields: Fields to include/exclude
            exclude: Whether to exclude fields instead of including

        Returns:
            Self for chaining

        Raises:
            ValueError: If no fields are specified
        """
        if not fields:
            raise ValueError("At least one field must be specified")
        projection = {field: 0 if exclude else 1 for field in fields}
        self._query.project(**projection)
        return self

    async def all(self) -> List[T]:
        """Get all records.

        Returns:
            List of records matching the query

        Raises:
            TypeError: If records cannot be converted to model instances
        """
        query = self._query.build()

        # Get collection
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[
            self._model_cls.get_collection_name()
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
        return [self._model_cls(**doc) for doc in documents]

    async def first(self) -> Optional[T]:
        """Get first record.

        Returns:
            First record or None if no records found

        Raises:
            TypeError: If record cannot be converted to model instance
        """
        self._query.limit(1)
        records = await self.all()
        return records[0] if records else None

    async def count(self) -> int:
        """Count records.

        Returns:
            Number of records matching the query

        Raises:
            TypeError: If collection name cannot be determined
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db

        # Get collection
        collection: AsyncIOMotorCollection[DocumentType] = db[
            self._model_cls.get_collection_name()
        ]

        # Count documents
        return await collection.count_documents(self._query.build()["filter"])

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            String representation of the record set
        """
        return f"RecordSet({self._model_cls.__name__}, {str(self._query)})"

    def __iter__(self) -> Any:
        """Iterate over records.

        Returns:
            Iterator over records

        Examples:
            >>> users = await User.search([])
            >>> for user in users:
            ...     print(user.name)
        """
        return iter(self._records)

    @property
    def ids(self) -> List[str]:
        """Get list of record IDs.

        Returns:
            List of record IDs

        Examples:
            >>> users = await User.search([])
            >>> user_ids = users.ids
        """
        return [str(record.id) for record in self._records]

    async def write(self, values: DocumentType) -> bool:
        """Update records with values.

        Args:
            values: Values to update

        Returns:
            True if update was successful

        Examples:
            >>> users = await User.search([["age", "<", 18]])
            >>> await users.write({"is_minor": True})
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[
            self._model_cls.get_collection_name()
        ]

        ids = [ObjectId(record.id) for record in self._records]
        result = await collection.update_many({"_id": {"$in": ids}}, {"$set": values})
        return result.modified_count > 0

    async def unlink(self) -> bool:
        """Delete records.

        Returns:
            True if deletion was successful

        Examples:
            >>> inactive_users = await User.search([["active", "=", False]])
            >>> await inactive_users.unlink()
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[
            self._model_cls.get_collection_name()
        ]

        ids = [ObjectId(record.id) for record in self._records]
        result = await collection.delete_many({"_id": {"$in": ids}})
        return result.deleted_count > 0

    def filtered(self, func: Callable[[T], bool]) -> RecordSet[T]:
        """Filter records using predicate function.

        Args:
            func: Predicate function that takes a record and returns a boolean

        Returns:
            New RecordSet with filtered records

        Examples:
            >>> users = await User.search([])
            >>> adults = users.filtered(lambda user: user.age >= 18)
        """
        filtered_records = [record for record in self._records if func(record)]
        return RecordSet(self._model_cls, filtered_records)

    def filtered_domain(
        self, domain: List[Union[List[Any], Tuple[Any, ...]]]
    ) -> RecordSet[T]:
        """Filter records using domain expression.

        Args:
            domain: Domain expression for filtering records

        Returns:
            New RecordSet with filtered records

        Examples:
            >>> users = await User.search([])
            >>> adults = users.filtered_domain([["age", ">=", 18]])
        """
        filtered_records: List[T] = []
        for record in self._records:
            match = True
            for condition in domain:
                if len(condition) != 3:
                    continue
                field: str = str(condition[0])
                op: str = str(condition[1])
                value: Any = condition[2]
                record_value = getattr(record, field, None)
                if not self._compare_values(record_value, op, value):
                    match = False
                    break
            if match:
                filtered_records.append(record)
        return RecordSet(self._model_cls, filtered_records)

    def sorted(self, key: str, reverse: bool = False) -> RecordSet[T]:
        """Sort records by field.

        Args:
            key: Field to sort by
            reverse: Whether to sort in reverse order

        Returns:
            New RecordSet with sorted records

        Examples:
            >>> users = await User.search([])
            >>> sorted_users = users.sorted("name")
        """
        sorted_records = sorted(
            self._records, key=lambda x: getattr(x, key), reverse=reverse
        )
        return RecordSet(self._model_cls, sorted_records)

    def mapped(self, field: str) -> List[Any]:
        """Map field values from records.

        Args:
            field: Field to map

        Returns:
            List of field values

        Examples:
            >>> users = await User.search([])
            >>> names = users.mapped("name")
        """
        return [getattr(record, field) for record in self._records]

    def _compare_values(self, value1: Any, op: str, value2: Any) -> bool:
        """Compare two values using the given operator.

        Args:
            value1: First value
            op: Operator
            value2: Second value

        Returns:
            True if comparison is true, False otherwise
        """
        if op == "=":
            return value1 == value2
        elif op == "!=":
            return value1 != value2
        elif op == ">":
            return value1 > value2
        elif op == ">=":
            return value1 >= value2
        elif op == "<":
            return value1 < value2
        elif op == "<=":
            return value1 <= value2
        elif op == "in":
            return value1 in value2
        elif op == "not in":
            return value1 not in value2
        elif op == "like":
            return value2 in str(value1)
        elif op == "not like":
            return value2 not in str(value1)
        return False
