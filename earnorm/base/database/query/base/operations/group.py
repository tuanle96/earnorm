"""Base group query interface.

This module provides base classes for group queries.

Examples:
    >>> # Simple group by
    >>> stats = await Order.group().by(
    ...     "status"
    ... ).count().execute()

    >>> # Complex grouping
    >>> stats = await Order.group().by(
    ...     "status",
    ...     "category"
    ... ).count(
    ...     alias="total_orders"
    ... ).sum(
    ...     "amount",
    ...     alias="total_amount"
    ... ).having(
    ...     total_orders__gt=10
    ... ).execute()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class GroupQuery(Generic[ModelT], ABC):
    """Base class for group queries."""

    def __init__(self) -> None:
        """Initialize group query."""
        self._group_fields: List[str] = []
        self._aggregates: List[Dict[str, Any]] = []
        self._having: Optional[JsonDict] = None

    def by(self, *fields: str) -> "GroupQuery[ModelT]":
        """Add group by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        self._group_fields.extend(fields)
        return self

    def count(self, alias: str = "count") -> "GroupQuery[ModelT]":
        """Add count aggregate.

        Args:
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._aggregates.append({"type": "count", "alias": alias})
        return self

    def sum(self, field: str, alias: Optional[str] = None) -> "GroupQuery[ModelT]":
        """Add sum aggregate.

        Args:
            field: Field to sum
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._aggregates.append(
            {"type": "sum", "field": field, "alias": alias or f"sum_{field}"}
        )
        return self

    def avg(self, field: str, alias: Optional[str] = None) -> "GroupQuery[ModelT]":
        """Add average aggregate.

        Args:
            field: Field to average
            alias: Result field name

        Returns:
            Self for chaining
        """
        self._aggregates.append(
            {"type": "avg", "field": field, "alias": alias or f"avg_{field}"}
        )
        return self

    def having(self, **conditions: Any) -> "GroupQuery[ModelT]":
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
        """Execute group query.

        Returns:
            List of grouped results
        """
        pass
