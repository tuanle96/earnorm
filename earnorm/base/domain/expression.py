"""Domain expression implementation."""

from typing import Any, List, Optional, Union

from earnorm.base.domain.operators import DomainOperator


class DomainExpression:
    """Domain expression for building complex queries.

    This class represents a domain expression that can be:
    - Combined with other expressions
    - Converted to MongoDB queries
    - Validated and normalized

    Examples:
        >>> expr = DomainExpression([["age", ">", 18], DomainOperator.AND, ["active", "=", True]])
        >>> expr.to_list()
        [["age", ">", 18], "AND", ["active", "=", True]]
    """

    def __init__(self, domain: Optional[List[Any]] = None) -> None:
        """Initialize domain expression.

        Args:
            domain: Initial domain expression
        """
        self._domain = domain or []

    def and_(self, other: Union["DomainExpression", List[Any]]) -> "DomainExpression":
        """Combine with AND operator.

        Args:
            other: Other domain expression

        Returns:
            New combined expression
        """
        if isinstance(other, DomainExpression):
            other = other._domain

        return DomainExpression(self._domain + [DomainOperator.AND] + other)

    def or_(self, other: Union["DomainExpression", List[Any]]) -> "DomainExpression":
        """Combine with OR operator.

        Args:
            other: Other domain expression

        Returns:
            New combined expression
        """
        if isinstance(other, DomainExpression):
            other = other._domain

        return DomainExpression(self._domain + [DomainOperator.OR] + other)

    def not_(self) -> "DomainExpression":
        """Negate expression.

        Returns:
            New negated expression
        """
        return DomainExpression([DomainOperator.NOT] + self._domain)

    def to_list(self) -> List[Any]:
        """Convert to list representation.

        Returns:
            Domain expression as list
        """
        return self._domain

    def __str__(self) -> str:
        """Get string representation."""
        return str(self._domain)

    def __repr__(self) -> str:
        """Get string representation."""
        return self.__str__()
