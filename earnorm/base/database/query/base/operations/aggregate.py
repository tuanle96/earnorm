"""Base aggregate query interface.

This module provides base classes for aggregation queries.

Examples:
    >>> # Count by status
    >>> stats = await User.aggregate()\\
    ...     .group("status")\\
    ...     .count()\\
    ...     .execute()
    
    >>> # Average age by country
    >>> avg_age = await User.aggregate()\\
    ...     .group("country")\\
    ...     .avg("age")\\
    ...     .having(count__gt=100)\\
    ...     .execute()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class AggregateQuery(Generic[ModelT], ABC):
    """Base class for aggregation queries."""

    def __init__(self) -> None:
        """Initialize aggregate query."""
        self._group_by: List[str] = []
        self._having: Optional[JsonDict] = None
        self._pipeline: List[Dict[str, Any]] = []

    def group(self, *fields: str) -> "AggregateQuery[ModelT]":
        """Group results by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        self._group_by.extend(fields)
        return self

    def sum(self, field: str, alias: Optional[str] = None) -> "AggregateQuery[ModelT]":
        """Add sum aggregation.

        Args:
            field: Field to sum
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._pipeline.append(
            {"type": "sum", "field": field, "alias": alias or f"sum_{field}"}
        )
        return self

    def avg(self, field: str, alias: Optional[str] = None) -> "AggregateQuery[ModelT]":
        """Add average aggregation.

        Args:
            field: Field to average
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._pipeline.append(
            {"type": "avg", "field": field, "alias": alias or f"avg_{field}"}
        )
        return self

    def count(self, alias: str = "count") -> "AggregateQuery[ModelT]":
        """Add count aggregation.

        Args:
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._pipeline.append({"type": "count", "alias": alias})
        return self

    def having(self, **conditions: Any) -> "AggregateQuery[ModelT]":
        """Add having conditions.

        Args:
            conditions: Having conditions

        Returns:
            Self for chaining
        """
        self._having = conditions
        return self

    @abstractmethod
    async def execute(self) -> List[JsonDict]:
        """Execute aggregation pipeline.

        Returns:
            List of aggregation results
        """
        pass
