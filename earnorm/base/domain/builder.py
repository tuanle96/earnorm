"""Domain builder for query building.

This module provides a fluent interface for building domain expressions.

Examples:
    >>> builder = DomainBuilder()
    >>> domain = (
    ...     builder
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
    >>> mongo_query = domain.to_mongo()
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

from typing import Any, List, Union

from earnorm.base.domain.expression import DomainExpression, LogicalOperator
from earnorm.types import DomainOperator


class DomainFieldBuilder:
    """Builder for field expressions.

    Examples:
        >>> builder = DomainFieldBuilder("age")
        >>> expr = builder.greater_than(18)
        >>> expr.to_mongo()
        {"age": {"$gt": 18}}
    """

    def __init__(self, field: str, parent: "DomainBuilder") -> None:
        """Initialize field builder.

        Args:
            field: Field name
            parent: Parent builder
        """
        self.field = field
        self.parent = parent

    def equals(self, value: Any) -> "DomainBuilder":
        """Field equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "=", value)
        return self.parent

    def not_equals(self, value: Any) -> "DomainBuilder":
        """Field not equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "!=", value)
        return self.parent

    def greater_than(self, value: Any) -> "DomainBuilder":
        """Field greater than value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, ">", value)
        return self.parent

    def greater_equals(self, value: Any) -> "DomainBuilder":
        """Field greater than or equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, ">=", value)
        return self.parent

    def less_than(self, value: Any) -> "DomainBuilder":
        """Field less than value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "<", value)
        return self.parent

    def less_equals(self, value: Any) -> "DomainBuilder":
        """Field less than or equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "<=", value)
        return self.parent

    def in_(self, values: List[Any]) -> "DomainBuilder":
        """Field in values.

        Args:
            values: List of values

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "in", values)
        return self.parent

    def not_in(self, values: List[Any]) -> "DomainBuilder":
        """Field not in values.

        Args:
            values: List of values

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "not in", values)
        return self.parent

    def like(self, pattern: str) -> "DomainBuilder":
        """Field matches pattern.

        Args:
            pattern: Pattern to match

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "like", pattern)
        return self.parent

    def ilike(self, pattern: str) -> "DomainBuilder":
        """Field matches pattern (case insensitive).

        Args:
            pattern: Pattern to match

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "ilike", pattern)
        return self.parent

    def not_like(self, pattern: str) -> "DomainBuilder":
        """Field does not match pattern.

        Args:
            pattern: Pattern to match

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "not like", pattern)
        return self.parent

    def not_ilike(self, pattern: str) -> "DomainBuilder":
        """Field does not match pattern (case insensitive).

        Args:
            pattern: Pattern to match

        Returns:
            Parent builder
        """
        self.parent.add_leaf(self.field, "not ilike", pattern)
        return self.parent


class DomainBuilder:
    """Builder for domain expressions.

    Examples:
        >>> builder = DomainBuilder()
        >>> domain = (
        ...     builder
        ...     .field("age").greater_than(18)
        ...     .and_()
        ...     .field("status").equals("active")
        ...     .build()
        ... )
        >>> mongo_query = domain.to_mongo()
        >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    """

    def __init__(self) -> None:
        """Initialize domain builder."""
        self.expressions: List[Union[List[Any], str]] = []

    def field(self, name: str) -> DomainFieldBuilder:
        """Start building field expression.

        Args:
            name: Field name

        Returns:
            Field builder
        """
        return DomainFieldBuilder(name, self)

    def add_leaf(self, field: str, operator: DomainOperator, value: Any) -> None:
        """Add leaf expression.

        Args:
            field: Field name
            operator: Operator
            value: Value
        """
        self.expressions.append([field, operator, value])

    def and_(self) -> "DomainBuilder":
        """Add AND operator.

        Returns:
            Self for chaining
        """
        self.expressions.append(LogicalOperator.AND)
        return self

    def or_(self) -> "DomainBuilder":
        """Add OR operator.

        Returns:
            Self for chaining
        """
        self.expressions.append(LogicalOperator.OR)
        return self

    def not_(self) -> "DomainBuilder":
        """Add NOT operator.

        Returns:
            Self for chaining
        """
        self.expressions.append(LogicalOperator.NOT)
        return self

    def open_group(self) -> "DomainBuilder":
        """Open expression group.

        Returns:
            Self for chaining
        """
        self.expressions.append("(")
        return self

    def close_group(self) -> "DomainBuilder":
        """Close expression group.

        Returns:
            Self for chaining
        """
        self.expressions.append(")")
        return self

    def build(self) -> DomainExpression:
        """Build domain expression.

        Returns:
            Domain expression
        """
        return DomainExpression(self.expressions)
