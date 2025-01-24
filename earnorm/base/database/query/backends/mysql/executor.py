"""MySQL query executor implementation.

This module provides MySQL query executor implementation.
It supports executing SQL queries with parameters.

Examples:
    ```python
    executor = MySQLQueryExecutor(conn)
    query = MySQLQuery("SELECT * FROM users WHERE age > %s", [18])
    results = await executor.execute(query)
    ```
"""

from typing import TypeVar

from aiomysql import Connection  # type: ignore

from earnorm.base.database.query.backends.mysql.query import MySQLQuery
from earnorm.base.database.query.base import QueryExecutor

T = TypeVar("T")


class MySQLQueryExecutor(QueryExecutor[Connection, MySQLQuery, T]):
    """MySQL query executor implementation.

    This class provides functionality for executing MySQL queries.
    It supports parameterized queries and fetch size control.

    Examples:
        ```python
        executor = MySQLQueryExecutor(conn)
        query = MySQLQuery("SELECT * FROM users WHERE age > %s", [18])
        results = await executor.execute(query)
        ```
    """

    def __init__(self, conn: Connection) -> None:
        """Initialize executor.

        Args:
            conn: MySQL connection
        """
        self.conn = conn

    async def execute(self, query: MySQLQuery) -> T:
        """Execute MySQL query.

        Args:
            query: MySQL query to execute

        Returns:
            Query results

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()

    async def validate(self, query: MySQLQuery) -> None:
        """Validate query.

        Args:
            query: Query to validate

        Raises:
            ValueError: If query is invalid
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()
