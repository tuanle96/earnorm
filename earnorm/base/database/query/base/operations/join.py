"""Base join query interface.

This module provides base classes for join queries.

Examples:
    >>> # Simple join
    >>> users = await User.join(
    ...     "posts",
    ...     on={"id": "user_id"},
    ...     type="left"
    ... ).execute()
    
    >>> # Multiple joins with conditions
    >>> users = await User.join(
    ...     "posts",
    ...     on={"id": "user_id"}
    ... ).join(
    ...     "comments",
    ...     on={"id": "user_id"}
    ... ).filter(
    ...     posts__likes__gt=10
    ... ).execute()
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from earnorm.base.domain.expression import DomainExpression
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class JoinQuery(Generic[ModelT], ABC):
    """Base class for join queries."""

    def __init__(self) -> None:
        """Initialize join query."""
        self._joins: List[Dict[str, Any]] = []
        self._domain: Optional[DomainExpression[ModelT]] = None
        self._select: List[str] = []

    def join(
        self, model: str, on: Dict[str, str], type: str = "inner"
    ) -> "JoinQuery[ModelT]":
        """Add join condition.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            type: Join type (inner, left, right)

        Returns:
            Self for chaining
        """
        self._joins.append({"model": model, "conditions": on, "type": type})
        return self

    def select(self, *fields: str) -> "JoinQuery[ModelT]":
        """Select fields to return.

        Args:
            fields: Fields to select

        Returns:
            Self for chaining
        """
        self._select.extend(fields)
        return self

    def filter(self, domain: DomainExpression[ModelT]) -> "JoinQuery[ModelT]":
        """Add filter conditions.

        Args:
            domain: Filter conditions

        Returns:
            Self for chaining
        """
        self._domain = domain
        return self

    @abstractmethod
    async def execute(self) -> List[JsonDict]:
        """Execute join query.

        Returns:
            List of joined results
        """
        pass
