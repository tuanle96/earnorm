"""Query interfaces.

This module defines the interfaces for all query operations.
All database-specific implementations must implement these interfaces.

Examples:
    >>> # Using query interface
    >>> query = Query[User]()
    >>> query.filter([("age", ">", 18)])
    >>> query.order_by("name")
    >>> query.limit(10)
    >>> results = await query.execute()
"""

from abc import abstractmethod
from typing import Any, List, Optional, Protocol, TypeVar, Union

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class QueryProtocol(Protocol[ModelT]):
    """Protocol for query operations."""

    @abstractmethod
    def filter(self, domain: Union[List[Any], JsonDict]) -> "QueryProtocol[ModelT]":
        """Add filter conditions.

        Args:
            domain: Filter conditions

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def order_by(self, *fields: str) -> "QueryProtocol[ModelT]":
        """Add order by fields.

        Args:
            fields: Fields to order by

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def limit(self, limit: int) -> "QueryProtocol[ModelT]":
        """Set result limit.

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def offset(self, offset: int) -> "QueryProtocol[ModelT]":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    async def execute(self) -> List[ModelT]:
        """Execute query and return results.

        Returns:
            Query results
        """
        ...

    @abstractmethod
    async def count(self) -> int:
        """Count results without fetching them.

        Returns:
            Number of results
        """
        ...

    @abstractmethod
    async def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        ...

    @abstractmethod
    async def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        ...
