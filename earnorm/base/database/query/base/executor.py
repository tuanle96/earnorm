"""Query executor protocol.

This module provides the base protocol for query executors.
Query executors are responsible for executing database-specific queries.

Examples:
    ```python
    class MongoQueryExecutor(QueryExecutor[AsyncIOMotorDatabase, MongoQuery, Dict[str, Any]]):
        async def execute(self, query: MongoQuery) -> Dict[str, Any]:
            collection = self.db[query.collection]
            return await collection.find_one(query.filter)
    ```
"""

from abc import abstractmethod
from typing import Protocol, TypeVar

DBType = TypeVar("DBType", covariant=True)
QueryType = TypeVar("QueryType", contravariant=True)
ResultType = TypeVar("ResultType", covariant=True)


class QueryExecutor(Protocol[DBType, QueryType, ResultType]):
    """Protocol for query executors.

    This protocol defines the interface that all query executors must implement.
    Query executors are responsible for executing database-specific queries.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)
        QueryType: Query type (e.g. MongoQuery)
        ResultType: Result type (e.g. Dict[str, Any])

    Examples:
        ```python
        class MongoQueryExecutor(QueryExecutor[AsyncIOMotorDatabase, MongoQuery, Dict[str, Any]]):
            async def execute(self, query: MongoQuery) -> Dict[str, Any]:
                collection = self.db[query.collection]
                return await collection.find_one(query.filter)
        ```
    """

    @abstractmethod
    async def execute(self, query: QueryType) -> ResultType:
        """Execute database query.

        This method should execute the query and return the results.

        Args:
            query: Database-specific query to execute

        Returns:
            Query results

        Examples:
            ```python
            executor = MongoQueryExecutor(db)
            result = await executor.execute(query)
            ```
        """
        pass

    @abstractmethod
    async def validate(self, query: QueryType) -> None:
        """Validate query before execution.

        This method should validate that the query is valid for execution.

        Args:
            query: Query to validate

        Raises:
            ValueError: If query is invalid

        Examples:
            ```python
            executor = MongoQueryExecutor(db)
            await executor.validate(query)  # Raises if invalid
            ```
        """
        pass
