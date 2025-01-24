"""MongoDB query executor implementation.

This module provides MongoDB query executor implementation.
It supports executing MongoDB queries and aggregation pipelines.

Examples:
    ```python
    executor = MongoQueryExecutor(db)
    query = MongoQuery("users", filter={"age": {"$gt": 18}})
    results = await executor.execute(query)
    ```
"""

import logging
from typing import Any, Generic, List, Sequence, TypeVar, cast

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.base import QueryExecutor

logger = logging.getLogger(__name__)
T = TypeVar("T")


class MongoQueryExecutor(
    QueryExecutor[AsyncIOMotorDatabase[Any], MongoQuery[T], Sequence[T]], Generic[T]
):
    """MongoDB query executor implementation.

    This class provides functionality for executing MongoDB queries.
    It supports both find and aggregate operations.

    Examples:
        ```python
        executor = MongoQueryExecutor(db)
        query = MongoQuery("users", filter={"age": {"$gt": 18}})
        results = await executor.execute(query)
        ```
    """

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        """Initialize executor.

        Args:
            db: MongoDB database connection
        """
        self.db = db

    async def execute(self, query: MongoQuery[T]) -> Sequence[T]:
        """Execute MongoDB query.

        Args:
            query: MongoDB query to execute

        Returns:
            Sequence of query results

        Raises:
            ValueError: If query is invalid
            PyMongoError: If query execution fails
        """
        try:
            await self.validate(query)

            collection: AsyncIOMotorCollection[Any] = self.db[query.collection]
            results: List[T] = []

            logger.debug(
                "Executing MongoDB query: collection=%s, filter=%s, projection=%s, "
                "sort=%s, skip=%s, limit=%s, pipeline=%s",
                query.collection,
                query.filter,
                query.projection,
                query.sort,
                query.skip,
                query.limit,
                query.pipeline,
            )

            if query.pipeline is not None:
                # Execute aggregation pipeline
                cursor = collection.aggregate(
                    query.pipeline,
                    allowDiskUse=query.allow_disk_use,
                    hint=query.hint,
                )
            else:
                # Execute find query
                cursor = collection.find(
                    filter=query.filter or {},
                    projection=query.projection,
                    sort=query.sort,
                    skip=query.skip,
                    limit=query.limit,
                    hint=query.hint,
                )

            async for doc in cursor:
                results.append(cast(T, doc))

            logger.debug("MongoDB query returned %d results", len(results))
            return results

        except PyMongoError as e:
            logger.error("MongoDB query execution failed: %s", str(e))
            raise

    async def validate(self, query: MongoQuery[T]) -> None:
        """Validate query.

        Args:
            query: Query to validate

        Raises:
            ValueError: If query is invalid
        """
        if not query.collection:
            raise ValueError("Collection name is required")

        if query.pipeline is not None and (
            query.filter
            or query.projection
            or query.sort
            or query.skip is not None
            or query.limit is not None
        ):
            raise ValueError(
                "Cannot use find options (filter, projection, sort, skip, limit) "
                "with aggregation pipeline"
            )
