"""Query builder for EarnORM."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo import ASCENDING, DESCENDING

from ..base.model import BaseModel
from ..db.connection import ConnectionManager

T = TypeVar("T", bound=BaseModel)
SortOrder = Union[int, str]


class QueryBuilder(Generic[T]):
    """Builder for MongoDB queries."""

    def __init__(
        self, model_cls: Type[T], session: Optional[AsyncIOMotorClientSession] = None
    ) -> None:
        """Initialize query builder.

        Args:
            model_cls: Model class to query
            session: Optional session for transactions
        """
        self._model_cls = model_cls
        self._session = session
        self._conn = ConnectionManager()
        self._collection = self._conn.get_collection(model_cls.get_collection())

        # Query parts
        self._filter: Dict[str, Any] = {}
        self._projection: Optional[Dict[str, Any]] = None
        self._sort: List[tuple[str, SortOrder]] = []
        self._skip: Optional[int] = None
        self._limit: Optional[int] = None
        self._batch_size: Optional[int] = None

    def filter(self, **kwargs: Any) -> "QueryBuilder[T]":
        """Add filter conditions.

        Args:
            **kwargs: Filter conditions

        Returns:
            QueryBuilder: Self for chaining
        """
        self._filter.update(kwargs)
        return self

    def project(self, *fields: str, exclude: bool = False) -> "QueryBuilder[T]":
        """Add projection.

        Args:
            *fields: Fields to include/exclude
            exclude: Whether to exclude fields

        Returns:
            QueryBuilder: Self for chaining
        """
        if not fields:
            return self

        if self._projection is None:
            self._projection = {}

        value = 0 if exclude else 1
        for field in fields:
            self._projection[field] = value

        return self

    def sort(self, *fields: Union[str, tuple[str, SortOrder]]) -> "QueryBuilder[T]":
        """Add sort conditions.

        Args:
            *fields: Fields to sort by. Can be field names (ascending)
                    or tuples of (field, order)

        Returns:
            QueryBuilder: Self for chaining
        """
        for field in fields:
            if isinstance(field, str):
                self._sort.append((field, ASCENDING))
            else:
                name, order = field
                if isinstance(order, str):
                    order = ASCENDING if order.lower() == "asc" else DESCENDING
                self._sort.append((name, order))
        return self

    def skip(self, count: int) -> "QueryBuilder[T]":
        """Add skip.

        Args:
            count: Number of documents to skip

        Returns:
            QueryBuilder: Self for chaining
        """
        self._skip = count
        return self

    def limit(self, count: int) -> "QueryBuilder[T]":
        """Add limit.

        Args:
            count: Maximum number of documents to return

        Returns:
            QueryBuilder: Self for chaining
        """
        self._limit = count
        return self

    def batch_size(self, size: int) -> "QueryBuilder[T]":
        """Set cursor batch size.

        Args:
            size: Batch size

        Returns:
            QueryBuilder: Self for chaining
        """
        self._batch_size = size
        return self

    async def count(self) -> int:
        """Count documents matching query.

        Returns:
            int: Number of matching documents
        """
        kwargs: Dict[str, Any] = {"filter": self._filter}
        if self._session is not None:
            kwargs["session"] = self._session

        return await self._collection.count_documents(**kwargs)

    async def exists(self) -> bool:
        """Check if any documents match query.

        Returns:
            bool: True if matching documents exist
        """
        return await self.count() > 0

    async def get(self) -> Optional[T]:
        """Get single document.

        Returns:
            Optional[Model]: Matching document or None
        """
        kwargs: Dict[str, Any] = {"filter": self._filter}
        if self._projection is not None:
            kwargs["projection"] = self._projection
        if self._session is not None:
            kwargs["session"] = self._session

        doc = await self._collection.find_one(**kwargs)
        if doc is None:
            return None

        return self._model_cls(**doc)

    async def all(self) -> List[T]:
        """Get all matching documents.

        Returns:
            List[Model]: List of matching documents
        """
        cursor = self._collection.find(
            filter=self._filter,
            projection=self._projection,
            session=self._session,
        )

        if self._sort:
            cursor = cursor.sort(self._sort)
        if self._skip is not None:
            cursor = cursor.skip(self._skip)
        if self._limit is not None:
            cursor = cursor.limit(self._limit)
        if self._batch_size is not None:
            cursor = cursor.batch_size(self._batch_size)

        docs = await cursor.to_list(None)
        return [self._model_cls(**doc) for doc in docs]

    async def first(self) -> Optional[T]:
        """Get first matching document.

        Returns:
            Optional[Model]: First matching document or None
        """
        return await self.limit(1).get()

    async def delete(self) -> int:
        """Delete matching documents.

        Returns:
            int: Number of deleted documents
        """
        kwargs: Dict[str, Any] = {"filter": self._filter}
        if self._session is not None:
            kwargs["session"] = self._session

        result = await self._collection.delete_many(**kwargs)
        return result.deleted_count

    async def update(self, update: Dict[str, Any], *, upsert: bool = False) -> int:
        """Update matching documents.

        Args:
            update: Update operations
            upsert: Whether to insert if no documents match

        Returns:
            int: Number of modified documents
        """
        kwargs: Dict[str, Any] = {
            "filter": self._filter,
            "update": update,
            "upsert": upsert,
        }
        if self._session is not None:
            kwargs["session"] = self._session

        result = await self._collection.update_many(**kwargs)
        return result.modified_count

    def clone(self) -> "QueryBuilder[T]":
        """Create copy of query builder.

        Returns:
            QueryBuilder: New query builder with same settings
        """
        builder = QueryBuilder(self._model_cls, self._session)
        builder._filter = self._filter.copy()
        if self._projection is not None:
            builder._projection = self._projection.copy()
        builder._sort = self._sort.copy()
        builder._skip = self._skip
        builder._limit = self._limit
        builder._batch_size = self._batch_size
        return builder
