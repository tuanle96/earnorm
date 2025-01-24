"""MySQL query implementation.

This module provides MySQL query implementation.
It supports SQL queries and parameters.

Examples:
    ```python
    query = MySQLQuery(
        sql="SELECT * FROM users WHERE age > %s",
        params=[18],
        fetch_size=1000
    )
    ```
"""

from typing import Any, List, Optional

from earnorm.base.database.query.base import Query


class MySQLQuery(Query[Any]):
    """MySQL query implementation.

    This class represents a MySQL query with SQL and parameters.
    It supports parameterized queries and fetch size control.

    Examples:
        ```python
        query = MySQLQuery(
            sql="SELECT * FROM users WHERE age > %s",
            params=[18],
            fetch_size=1000
        )
        ```
    """

    def __init__(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        fetch_size: Optional[int] = None,
    ) -> None:
        """Initialize query.

        Args:
            sql: SQL query string
            params: Query parameters
            fetch_size: Number of rows to fetch at a time
        """
        self.sql = sql
        self.params = params or []
        self.fetch_size = fetch_size

    def validate(self) -> None:
        """Validate query.

        Raises:
            ValueError: If query is invalid
        """
        if not self.sql:
            raise ValueError("SQL query is required")

        if self.fetch_size is not None and self.fetch_size <= 0:
            raise ValueError("Fetch size must be positive")

    def clone(self) -> "MySQLQuery":
        """Create a copy of this query.

        Returns:
            New query instance with same parameters
        """
        return MySQLQuery(
            sql=self.sql,
            params=self.params.copy() if self.params else None,
            fetch_size=self.fetch_size,
        )
