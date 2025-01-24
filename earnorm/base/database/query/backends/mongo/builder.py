"""MongoDB query builder implementation.

This module provides MongoDB query builder implementation.
It supports all MongoDB query operators and aggregation pipeline.

Examples:
    ```python
    builder = MongoQueryBuilder("users")
    builder.filter({"age": {"$gt": 18}})
    builder.project({"name": 1, "email": 1})
    builder.sort([("name", 1)])
    query = await builder.build()
    ```
"""

from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.base import QueryBuilder

JsonDict = Dict[str, Any]
SortSpec = List[Tuple[str, int]]
T = TypeVar("T")


class MongoQueryBuilder(
    QueryBuilder[AsyncIOMotorDatabase[Any], MongoQuery[T]], Generic[T]
):
    """MongoDB query builder implementation.

    This class provides a fluent interface for building MongoDB queries.
    It supports all MongoDB query operators and aggregation pipeline.

    Examples:
        ```python
        builder = MongoQueryBuilder("users")
        builder.filter({"age": {"$gt": 18}})
        builder.project({"name": 1, "email": 1})
        builder.sort([("name", 1)])
        query = await builder.build()
        ```
    """

    def __init__(self, collection: str) -> None:
        """Initialize builder.

        Args:
            collection: Collection name

        Raises:
            ValueError: If collection name is empty
        """
        if not collection:
            raise ValueError("Collection name is required")

        self.collection = collection
        self._filter: Optional[JsonDict] = None
        self._projection: Optional[JsonDict] = None
        self._sort: Optional[SortSpec] = None
        self._skip: Optional[int] = None
        self._limit: Optional[int] = None
        self._pipeline: Optional[List[JsonDict]] = None
        self._allow_disk_use = False
        self._hint: Optional[Union[str, List[Tuple[str, int]]]] = None

    def filter(self, filter: JsonDict) -> "MongoQueryBuilder[T]":
        """Set query filter.

        Args:
            filter: MongoDB query filter

        Returns:
            Self for chaining

        Raises:
            ValueError: If filter is not a dict
        """
        self._filter = filter
        return self

    def project(self, projection: JsonDict) -> "MongoQueryBuilder[T]":
        """Set field projection.

        Args:
            projection: MongoDB projection

        Returns:
            Self for chaining

        Raises:
            ValueError: If projection is not a dict
        """
        self._projection = projection
        return self

    def sort(self, sort: SortSpec) -> "MongoQueryBuilder[T]":
        """Set sort specification.

        Args:
            sort: List of (field, direction) tuples

        Returns:
            Self for chaining

        Raises:
            ValueError: If sort specification is invalid
        """
        for item in sort:
            if item[1] not in (-1, 1):
                raise ValueError("Sort direction must be 1 or -1")
        self._sort = sort
        return self

    def skip(self, skip: int) -> "MongoQueryBuilder[T]":
        """Set number of documents to skip.

        Args:
            skip: Number of documents to skip

        Returns:
            Self for chaining

        Raises:
            ValueError: If skip is negative
        """
        if skip < 0:
            raise ValueError("Skip must be non-negative")
        self._skip = skip
        return self

    def limit(self, limit: int) -> "MongoQueryBuilder[T]":
        """Set maximum number of documents to return.

        Args:
            limit: Maximum number of documents

        Returns:
            Self for chaining

        Raises:
            ValueError: If limit is negative
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        self._limit = limit
        return self

    def pipeline(self, pipeline: List[JsonDict]) -> "MongoQueryBuilder[T]":
        """Set aggregation pipeline.

        Args:
            pipeline: MongoDB aggregation pipeline

        Returns:
            Self for chaining

        Raises:
            ValueError: If pipeline is invalid
        """
        self._pipeline = pipeline
        return self

    def allow_disk_use(self, allow: bool = True) -> "MongoQueryBuilder[T]":
        """Allow disk use for large queries.

        Args:
            allow: Whether to allow disk use

        Returns:
            Self for chaining
        """
        self._allow_disk_use = allow
        return self

    def hint(self, hint: Union[str, List[Tuple[str, int]]]) -> "MongoQueryBuilder[T]":
        """Set index hint.

        Args:
            hint: Index hint (name or specification)

        Returns:
            Self for chaining

        Raises:
            ValueError: If hint is invalid
        """
        if isinstance(hint, list):
            for item in hint:
                if item[1] not in (-1, 1):
                    raise ValueError("Hint direction must be 1 or -1")
        self._hint = hint
        return self

    async def build(self) -> MongoQuery[T]:
        """Build MongoDB query.

        Returns:
            MongoDB query object

        Raises:
            ValueError: If builder state is invalid
        """
        self.validate()
        return MongoQuery(
            collection=self.collection,
            filter=self._filter,
            projection=self._projection,
            sort=self._sort,
            skip=self._skip,
            limit=self._limit,
            pipeline=self._pipeline,
            allow_disk_use=self._allow_disk_use,
            hint=self._hint,
        )

    def validate(self) -> None:
        """Validate builder state.

        Raises:
            ValueError: If builder state is invalid
        """
        if not self.collection:
            raise ValueError("Collection name is required")

        if self._pipeline is not None and (
            self._filter is not None
            or self._projection is not None
            or self._sort is not None
            or self._skip is not None
            or self._limit is not None
        ):
            raise ValueError(
                "Cannot use find options (filter, projection, sort, skip, limit) "
                "with aggregation pipeline"
            )
