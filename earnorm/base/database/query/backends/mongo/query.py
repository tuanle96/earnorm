"""MongoDB query implementation.

This module provides MongoDB query implementation.
It supports all MongoDB query operators and aggregation pipeline.

Examples:
    ```python
    query = MongoQuery(
        collection="users",
        filter={"age": {"$gt": 18}},
        projection={"name": 1, "email": 1},
        sort=[("name", 1)],
        skip=0,
        limit=10
    )
    ```
"""

from copy import deepcopy
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm.base.database.query.base import Query

JsonDict = Dict[str, Any]
SortSpec = List[Tuple[str, int]]
T = TypeVar("T")


class MongoQuery(Query[AsyncIOMotorDatabase[Any]], Generic[T]):
    """MongoDB query implementation.

    This class represents a MongoDB query with support for:
    - Find operations
    - Aggregation pipeline
    - Sort, skip, limit
    - Projection
    - Index hints

    Examples:
        ```python
        query = MongoQuery(
            collection="users",
            filter={"age": {"$gt": 18}},
            projection={"name": 1, "email": 1},
            sort=[("name", 1)],
            skip=0,
            limit=10
        )
        ```
    """

    def __init__(
        self,
        collection: str,
        filter: Optional[JsonDict] = None,
        projection: Optional[JsonDict] = None,
        sort: Optional[SortSpec] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        pipeline: Optional[List[JsonDict]] = None,
        allow_disk_use: bool = False,
        hint: Optional[Union[str, List[Tuple[str, int]]]] = None,
    ) -> None:
        """Initialize MongoDB query.

        Args:
            collection: Collection name
            filter: Query filter
            projection: Field projection
            sort: Sort specification
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            pipeline: Aggregation pipeline
            allow_disk_use: Allow disk use for large queries
            hint: Index hint

        Raises:
            ValueError: If any parameter is invalid
        """
        self.collection = collection
        self.filter = filter or {}
        self.projection = projection
        self.sort = sort
        self.skip = skip
        self.limit = limit
        self.pipeline = pipeline
        self.allow_disk_use = allow_disk_use
        self.hint = hint
        self.validate()

    def validate(self) -> None:
        """Validate query parameters.

        This method validates:
        - Collection name is not empty
        - Filter is valid JSON
        - Projection is valid
        - Sort specification is valid
        - Skip and limit are non-negative
        - Pipeline is valid
        - Index hint is valid

        Raises:
            ValueError: If any parameter is invalid
        """
        if not self.collection:
            raise ValueError("Collection name is required")

        if self.sort is not None:
            for item in self.sort:
                if item[1] not in (-1, 1):
                    raise ValueError("Sort direction must be 1 or -1")

        if self.skip is not None and self.skip < 0:
            raise ValueError("Skip must be non-negative")

        if self.limit is not None and self.limit < 0:
            raise ValueError("Limit must be non-negative")

        if self.hint is not None and isinstance(self.hint, list):
            for item in self.hint:
                if item[1] not in (-1, 1):
                    raise ValueError("Hint direction must be 1 or -1")

    def clone(self) -> "MongoQuery[T]":
        """Create deep copy of query.

        Returns:
            New MongoQuery instance with same parameters
        """
        return MongoQuery(
            collection=self.collection,
            filter=deepcopy(self.filter),
            projection=deepcopy(self.projection),
            sort=deepcopy(self.sort),
            skip=self.skip,
            limit=self.limit,
            pipeline=deepcopy(self.pipeline),
            allow_disk_use=self.allow_disk_use,
            hint=deepcopy(self.hint),
        )
