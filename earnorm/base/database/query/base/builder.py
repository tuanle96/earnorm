"""Query builder protocol.

This module provides the base protocol for query builders.
Query builders are responsible for constructing database-specific queries.

Examples:
    ```python
    class MongoQueryBuilder(QueryBuilder[AsyncIOMotorDatabase, MongoQuery]):
        async def build(self) -> MongoQuery:
            return MongoQuery(
                collection=self.collection,
                filter=self.filter,
                projection=self.projection
            )
    ```
"""

from abc import abstractmethod
from typing import Protocol, TypeVar

DBType = TypeVar("DBType", covariant=True)
QueryType = TypeVar("QueryType", covariant=True)


class QueryBuilder(Protocol[DBType, QueryType]):
    """Protocol for query builders.

    This protocol defines the interface that all query builders must implement.
    Query builders are responsible for constructing database-specific queries.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)
        QueryType: Query type (e.g. MongoQuery)

    Examples:
        ```python
        class MongoQueryBuilder(QueryBuilder[AsyncIOMotorDatabase, MongoQuery]):
            async def build(self) -> MongoQuery:
                return MongoQuery(
                    collection=self.collection,
                    filter=self.filter,
                    projection=self.projection
                )
        ```
    """

    @abstractmethod
    async def build(self) -> QueryType:
        """Build database query.

        This method should construct a database-specific query object
        using the builder's current state.

        Returns:
            Database-specific query object

        Examples:
            ```python
            builder = MongoQueryBuilder("users")
            builder.filter({"age": {"$gt": 18}})
            query = await builder.build()
            ```
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate builder state.

        This method should validate that the builder's current state
        can produce a valid query.

        Raises:
            ValueError: If builder state is invalid

        Examples:
            ```python
            builder = MongoQueryBuilder("users")
            builder.validate()  # Raises if invalid
            ```
        """
        pass
