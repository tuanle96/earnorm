"""MySQL query builder implementation.

This module provides MySQL query builder implementation.
It supports building SQL queries with parameters.

Examples:
    ```python
    builder = MySQLQueryBuilder()
    builder.select("users", ["name", "email"])
    builder.where("age > %s", [18])
    builder.order_by(["name ASC"])
    query = await builder.build()
    ```
"""

from typing import Any, List, Optional

from aiomysql import Connection  # type: ignore

from earnorm.base.database.query.backends.mysql.query import MySQLQuery
from earnorm.base.database.query.base import QueryBuilder


class MySQLQueryBuilder(QueryBuilder[Connection, MySQLQuery]):
    """MySQL query builder implementation.

    This class provides a fluent interface for building MySQL queries.
    It supports SELECT, INSERT, UPDATE, and DELETE operations.

    Examples:
        ```python
        builder = MySQLQueryBuilder()
        builder.select("users", ["name", "email"])
        builder.where("age > %s", [18])
        builder.order_by(["name ASC"])
        query = await builder.build()
        ```
    """

    def __init__(self) -> None:
        """Initialize builder."""
        self._table: Optional[str] = None
        self._columns: Optional[List[str]] = None
        self._where: Optional[str] = None
        self._where_params: List[Any] = []
        self._order_by: Optional[List[str]] = None
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._fetch_size: Optional[int] = None

    def select(
        self, table: str, columns: Optional[List[str]] = None
    ) -> "MySQLQueryBuilder":
        """Set SELECT query parameters.

        Args:
            table: Table name
            columns: Columns to select (None for *)

        Returns:
            Self for chaining
        """
        self._table = table
        self._columns = columns
        return self

    def where(
        self, condition: str, params: Optional[List[Any]] = None
    ) -> "MySQLQueryBuilder":
        """Set WHERE clause.

        Args:
            condition: WHERE condition
            params: Query parameters

        Returns:
            Self for chaining
        """
        self._where = condition
        if params:
            self._where_params.extend(params)
        return self

    def order_by(self, order_by: List[str]) -> "MySQLQueryBuilder":
        """Set ORDER BY clause.

        Args:
            order_by: ORDER BY expressions

        Returns:
            Self for chaining
        """
        self._order_by = order_by
        return self

    def limit(self, limit: int) -> "MySQLQueryBuilder":
        """Set LIMIT clause.

        Args:
            limit: Maximum number of rows

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> "MySQLQueryBuilder":
        """Set OFFSET clause.

        Args:
            offset: Number of rows to skip

        Returns:
            Self for chaining
        """
        self._offset = offset
        return self

    def fetch_size(self, size: int) -> "MySQLQueryBuilder":
        """Set fetch size.

        Args:
            size: Number of rows to fetch at a time

        Returns:
            Self for chaining
        """
        self._fetch_size = size
        return self

    async def build(self) -> MySQLQuery:
        """Build MySQL query.

        Returns:
            MySQL query object

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()

    def validate(self) -> None:
        """Validate builder state.

        Raises:
            ValueError: If builder state is invalid
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError()
