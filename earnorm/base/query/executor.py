"""Query executor implementation."""

from typing import Generic, List, TypeVar

from bson.raw_bson import RawBSONDocument
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor

from earnorm.base.query.builder import QueryBuilder
from earnorm.base.query.result import QueryResult
from earnorm.base.types import ModelProtocol

M = TypeVar("M", bound=ModelProtocol)


class QueryExecutor(Generic[M]):
    """MongoDB query executor.

    This class handles:
    - Executing queries on MongoDB collections
    - Converting results to model instances
    - Handling pagination and sorting

    Type Parameters:
        M: Type of model this executor handles

    Examples:
        >>> executor = QueryExecutor(collection, User)
        >>> query = QueryBuilder().filter(age=18).build()
        >>> result = await executor.execute(query)
        >>> users = result.items
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[RawBSONDocument],
        model_class: type[M],
    ) -> None:
        """Initialize executor.

        Args:
            collection: MongoDB collection
            model_class: Model class for results
        """
        self._collection = collection
        self._model_class = model_class

    async def execute(
        self, query: QueryBuilder, batch_size: int = 100
    ) -> QueryResult[M]:
        """Execute query and return results.

        Args:
            query: Query to execute
            batch_size: Number of documents to fetch per batch

        Returns:
            Query result with items and metadata

        Raises:
            ValueError: If query parameters are invalid
            TypeError: If query result cannot be converted to model instances

        Examples:
            >>> query = QueryBuilder().filter(age=18).build()
            >>> result = await executor.execute(query)
            >>> for user in result.items:
            ...     print(user.name)
        """
        # Get query components
        query_dict = query.build()
        filter_query = query_dict["filter"]
        sort = query_dict.get("sort")
        limit = query_dict.get("limit")
        skip = query_dict.get("offset")
        projection = query_dict.get("projection")

        # Build cursor
        cursor: AsyncIOMotorCursor[RawBSONDocument] = self._collection.find(
            filter=filter_query,
            projection=projection,
            skip=skip,
            limit=limit,
            batch_size=batch_size,
        )

        # Apply sort
        if sort:
            cursor.sort(sort)

        # Get total count (before limit/skip)
        total = await self._collection.count_documents(filter_query)

        # Get items
        raw_docs: List[RawBSONDocument] = await cursor.to_list(  # type: ignore
            length=limit or batch_size
        )
        items = [self._model_class(**dict(doc)) for doc in raw_docs]

        return QueryResult[M](items=items, total=total, limit=limit, offset=skip)
