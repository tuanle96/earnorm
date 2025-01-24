"""PostgreSQL query executor implementation.

This module provides PostgreSQL query executor implementation.
It supports executing SQL queries with parameters.

Examples:
    ```python
    executor = PostgresQueryExecutor(conn)
    query = PostgresQuery("SELECT * FROM users WHERE age > %s", [18])
    results = await executor.execute(query)
    ```
"""

from typing import TypeVar

from asyncpg import Connection  # type: ignore

from earnorm.base.database.query.backends.postgres.query import PostgresQuery
from earnorm.base.database.query.base import QueryExecutor

T = TypeVar("T")


class PostgresQueryExecutor(QueryExecutor[Connection, PostgresQuery, T]):
    """PostgreSQL query executor implementation.

    This class provides functionality for executing PostgreSQL queries.
    It supports parameterized queries and fetch size control.

    Examples:
        ```python
        executor = PostgresQueryExecutor(conn)
        query = PostgresQuery("SELECT * FROM users WHERE age > %s", [18])
        results = await executor.execute(query)
        ```
    """

    def __init__(self, conn: Connection) -> None:
        """Initialize executor.

        Args:
            conn: PostgreSQL connection
        """
        self.conn = conn

    async def execute(self, query: PostgresQuery) -> T:
        """Execute PostgreSQL query.

        Args:
            query: PostgreSQL query to execute

        Returns:
            Query results

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()

    async def validate(self, query: PostgresQuery) -> None:
        """Validate query.

        Args:
            query: Query to validate

        Raises:
            ValueError: If query is invalid
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()
