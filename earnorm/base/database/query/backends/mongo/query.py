"""MongoDB query implementation.

This module provides MongoDB-specific implementation for database queries.
It uses MongoDB's aggregation framework for complex queries.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> query = MongoQuery[User]()
    >>> # Filter and sort
    >>> query.where(User.age > 18).order_by(User.name)
    >>> # Join with another collection
    >>> query.join(Post).on(User.id == Post.user_id)
    >>> # Group and aggregate
    >>> query.aggregate().group_by(User.age).having(User.age > 20)
    >>> query.aggregate().group_by(User.age).count()
    >>> # Window functions
    >>> query.window().over(partition_by=[User.age]).row_number()
"""

from typing import Any, List, Optional, Type, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCommandCursor

from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.types import DatabaseModel, JsonDict

from .operations.aggregate import MongoAggregate
from .operations.join import MongoJoin
from .operations.window import MongoWindow

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class MongoQuery(BaseQuery[ModelT]):
    """MongoDB query implementation.

    This class provides MongoDB-specific implementation for database queries.
    It uses MongoDB's aggregation framework for complex queries.

    Args:
        ModelT: Type of model being queried
    """

    # pylint: disable=dangerous-default-value
    def __init__(
        self,
        collection: AsyncIOMotorCollection[JsonDict],  # type: ignore
        model_type: Type[ModelT],
        filter: JsonDict = {},  # pylint: disable=redefined-builtin
        projection: JsonDict = {},
        sort: List[tuple[str, int]] = [],
        skip: int = 0,
        limit: int = 0,
        pipeline: List[JsonDict] = [],
        allow_disk_use: bool = False,
        hint: Optional[Union[str, List[tuple[str, int]]]] = None,
        operation: Optional[str] = None,
        document: JsonDict = {},
        update: JsonDict = {},
        options: dict[str, Any] = {},
    ) -> None:
        """Initialize MongoDB query.

        Args:
            collection: MongoDB collection
            model_type: Model class being queried
            filter: Query filter
            projection: Field projection
            sort: Sort specification
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            pipeline: Aggregation pipeline
            allow_disk_use: Allow disk use for large queries
            hint: Index hint
            operation: Operation type (insert_one, update, delete)
            document: Document to insert
            update: Update operation
            options: Additional options
        """
        super().__init__(model_type)
        self._collection = collection
        self._model_type = model_type
        self._filter = filter
        self._projection = projection
        self._sort = sort
        self._skip = skip
        self._limit = limit
        self._pipeline = pipeline
        self._allow_disk_use = allow_disk_use
        self._hint = hint
        self._operation = operation
        self._document = document
        self._update = update
        self._options = options

    async def execute(self) -> List[ModelT]:
        """Execute MongoDB query.

        Returns:
            List of query results
        """
        # Build pipeline
        pipeline: List[JsonDict] = []

        # Add filter stage
        if self._filter:
            pipeline.append({"$match": self._filter})

        # Add projection stage
        if self._projection:
            pipeline.append({"$project": self._projection})

        # Add sort stage
        if self._sort:
            pipeline.append({"$sort": dict(self._sort)})

        # Add skip stage
        if self._skip:
            pipeline.append({"$skip": self._skip})

        # Add limit stage
        if self._limit:
            pipeline.append({"$limit": self._limit})

        # Add custom pipeline stages
        if self._pipeline:
            pipeline.extend(self._pipeline)

        # Execute pipeline
        cursor: AsyncIOMotorCommandCursor[JsonDict] = self._collection.aggregate(
            pipeline,
            allowDiskUse=self._allow_disk_use,
            hint=self._hint,
            **self._options,
        )
        docs = [doc async for doc in cursor]
        return [self._model_type(**doc) for doc in docs]

    def filter(self, domain: Union[List[Any], JsonDict]) -> "MongoQuery[ModelT]":
        """Filter documents.

        Args:
            domain: Filter conditions

        Returns:
            Self for chaining
        """
        if isinstance(domain, dict):
            self._filter.update(domain)
        else:
            self._domain = domain
        return self

    def order_by(self, *fields: str) -> "MongoQuery[ModelT]":
        """Add order by fields.

        Args:
            fields: Fields to order by

        Returns:
            Self for chaining
        """
        for field in fields:
            if field.startswith("-"):
                self._sort.append((field[1:], -1))
            else:
                self._sort.append((field, 1))
        return self

    def limit(self, limit: int) -> "MongoQuery[ModelT]":
        """Set result limit.

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> "MongoQuery[ModelT]":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self._skip = offset
        return self

    async def count(self) -> int:
        """Count documents.

        Returns:
            Number of documents
        """
        pipeline: List[JsonDict] = []

        # Add filter stage
        if self._filter:
            pipeline.append({"$match": self._filter})

        # Add count stage
        pipeline.append({"$count": "count"})

        # Execute pipeline
        cursor: AsyncIOMotorCommandCursor[JsonDict] = self._collection.aggregate(
            pipeline
        )
        result = [doc async for doc in cursor]
        return result[0]["count"] if result else 0

    async def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        return await self.count() > 0

    async def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        self._limit = 1
        results = await self.execute()
        return results[0] if results else None

    def join(
        self,
        model: Union[str, Type[JoinT]],
        on: Optional[dict[str, Any]] = None,
        join_type: str = "inner",
    ) -> JoinProtocol[ModelT, JoinT]:
        """Create join operation.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Join operation
        """
        join = MongoJoin[ModelT, JoinT](self._collection, self._model_type)
        join.join(model, on, join_type)
        self._joins.append(join)
        return join

    def aggregate(self) -> AggregateProtocol[ModelT]:
        """Create aggregate operation.

        Returns:
            Aggregate operation
        """
        aggregate = MongoAggregate[ModelT](self._collection, self._model_type)
        self._aggregates.append(aggregate)
        return aggregate

    def window(self) -> WindowProtocol[ModelT]:
        """Create window operation.

        Returns:
            Window operation
        """
        window = MongoWindow[ModelT]()
        self._windows.append(window)
        return window

    async def insert(self, document: JsonDict) -> JsonDict:
        """Insert document.

        Args:
            document: Document to insert

        Returns:
            Inserted document
        """
        result = await self._collection.insert_one(document)
        return {"_id": result.inserted_id}

    async def update(self, update: JsonDict) -> JsonDict:
        """Update documents.

        Args:
            update: Update operation

        Returns:
            Update result
        """
        result = await self._collection.update_many(self._filter, update)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
        }

    async def delete(self) -> JsonDict:
        """Delete documents.

        Returns:
            Delete result
        """
        result = await self._collection.delete_many(self._filter)
        return {"deleted_count": result.deleted_count}
