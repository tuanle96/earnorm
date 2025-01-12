"""Query builder implementation."""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pymongo.collection import Collection

from ..base.model import BaseModel

T = TypeVar("T", bound=BaseModel)


class QueryBuilder:
    """Builds MongoDB queries with a fluent interface."""

    def __init__(
        self, model_class: Type[T], filter_dict: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize query builder.

        Args:
            model_class: Model class to query
            filter_dict: Initial filter conditions
        """
        self.model_class = model_class
        self._filter = filter_dict or {}
        self._sort = []
        self._skip = 0
        self._limit = 0

    def filter(self, **kwargs: Any) -> "QueryBuilder":
        """Add filter conditions."""
        self._filter.update(kwargs)
        return self

    def sort(self, *fields: str) -> "QueryBuilder":
        """Add sort criteria."""
        for field in fields:
            if field.startswith("-"):
                self._sort.append((field[1:], -1))
            else:
                self._sort.append((field, 1))
        return self

    def skip(self, skip: int) -> "QueryBuilder":
        """Set number of documents to skip."""
        self._skip = skip
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set maximum number of documents to return."""
        self._limit = limit
        return self

    def _get_collection(self) -> Collection:
        """Get MongoDB collection."""
        if not self.model_class._connection:
            raise ValueError("No database connection")
        return self.model_class._connection.get_collection(
            self.model_class.get_collection()
        )

    def count(self) -> int:
        """Count documents matching the query."""
        return self._get_collection().count_documents(self._filter)

    def exists(self) -> bool:
        """Check if any documents match the query."""
        return bool(self.count())

    def first(self) -> Optional[T]:
        """Get first matching document."""
        doc = self._get_collection().find_one(
            self._filter, sort=self._sort if self._sort else None
        )
        return self.model_class(**doc) if doc else None

    def all(self) -> List[T]:
        """Get all matching documents."""
        cursor = self._get_collection().find(self._filter)

        if self._sort:
            cursor = cursor.sort(self._sort)
        if self._skip:
            cursor = cursor.skip(self._skip)
        if self._limit:
            cursor = cursor.limit(self._limit)

        return [self.model_class(**doc) for doc in cursor]
