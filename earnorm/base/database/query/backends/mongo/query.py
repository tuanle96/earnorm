"""MongoDB query implementation.

This module provides MongoDB-specific query implementation that integrates with
domain expressions for query building.

Examples:
    >>> # Using MongoQuery directly
    >>> query = MongoQuery[User](collection)
    >>> query.filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
    >>> query.sort("name", ascending=True)
    >>> query.limit(10)
    >>> query.offset(20)
    >>> results = await query.execute_async()
"""

from typing import List, Optional, Type, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING

from earnorm.base.database.query.backends.mongo.converter import MongoConverter
from earnorm.base.database.query.base.query import AsyncQuery
from earnorm.base.domain.expression import DomainExpression
from earnorm.types import DatabaseModel, JsonDict, ValueType

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoQuery(AsyncQuery[ModelT]):
    """MongoDB query implementation.

    This class implements the Query interface for MongoDB using Motor for async operations.
    It converts domain expressions to MongoDB filter format and executes queries.

    Args:
        collection: MongoDB collection to query
        model_cls: Model class for type hints
    """

    def __init__(
        self, collection: AsyncIOMotorCollection[JsonDict], model_cls: Type[ModelT]
    ) -> None:
        """Initialize query.

        Args:
            collection: MongoDB collection to query
            model_cls: Model class for type hints
        """
        super().__init__()
        self._collection = collection
        self._model_cls = model_cls
        self._converter = MongoConverter()
        self._raw_filter: Optional[JsonDict] = None

    def filter(
        self, domain: Union[DomainExpression[ValueType], JsonDict]
    ) -> "MongoQuery[ModelT]":
        """Add filter conditions.

        Args:
            domain: Domain expression or MongoDB filter dict

        Returns:
            Self for chaining
        """
        if isinstance(domain, DomainExpression):
            super().filter(domain)
        else:
            self._raw_filter = domain
        return self

    def to_filter(self) -> JsonDict:
        """Convert domain expression to MongoDB filter.

        Returns:
            MongoDB filter format
        """
        if self._raw_filter is not None:
            return self._raw_filter
        if not self._domain:
            return {}
        return self._converter.convert(self._domain.root)

    def to_sort(self) -> List[tuple[str, int]]:
        """Convert sort fields to MongoDB sort.

        Returns:
            List of (field, direction) tuples
        """
        return [
            (field, ASCENDING if ascending else DESCENDING)
            for field, ascending in self._sort_fields
        ]

    async def execute_async(self) -> List[ModelT]:
        """Execute query and return results asynchronously.

        Returns:
            Query results
        """
        cursor = self._collection.find(
            filter=self.to_filter(),
            sort=self.to_sort(),
            skip=self._offset,
            limit=self._limit,
        )
        results: List[ModelT] = []
        async for doc in cursor:
            model = self._model_cls()
            model.from_dict(doc)
            results.append(model)
        return results

    async def count_async(self) -> int:
        """Count results without fetching them asynchronously.

        Returns:
            Number of results
        """
        count = await self._collection.count_documents(self.to_filter())
        return count

    async def exists_async(self) -> bool:
        """Check if any results exist asynchronously.

        Returns:
            True if results exist
        """
        count = await self.count_async()
        return count > 0

    async def first_async(self) -> Optional[ModelT]:
        """Get first result or None asynchronously.

        Returns:
            First result or None
        """
        doc = await self._collection.find_one(
            filter=self.to_filter(), sort=self.to_sort(), skip=self._offset
        )
        if not doc:
            return None
        model = self._model_cls()
        model.from_dict(doc)
        return model
