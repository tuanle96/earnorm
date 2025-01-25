"""Domain builder for query building.

This module provides a fluent interface for building domain expressions.

Examples:
    >>> # Simple builder
    >>> domain = DomainBuilder.create([
    ...     ("age", ">", 18),
    ...     "&",
    ...     ("status", "=", "active")
    ... ])
    >>> visitor = MongoDomainVisitor()
    >>> mongo_query = domain.accept(visitor)
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    
    >>> # Fluent interface
    >>> domain = (
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
"""

from typing import Generic, List, Optional, TypeVar, Union, cast

from earnorm.base.domain.expression import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
    LogicalOp,
    Operator,
)
from earnorm.types import ValueType

T = TypeVar("T", bound=ValueType)


class DomainBuilder(Generic[T]):
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
    """

    def __init__(self) -> None:
        """Initialize builder."""
        self._nodes: List[Union[DomainNode[T], DomainLeaf[T]]] = []
        self._current_op: Optional[LogicalOp] = None

    @classmethod
    def create(
        cls, domain: List[Union[tuple[str, Operator, T], LogicalOp]]
    ) -> DomainExpression[T]:
        """Create domain expression from list.

        Args:
            domain: Domain expression in list format

        Returns:
            Domain expression

        Examples:
            >>> domain = DomainBuilder.create([
            ...     ("age", ">", 18),
            ...     "&",
            ...     ("status", "=", "active")
            ... ])
        """
        return DomainExpression(domain)

    def field(self, name: str) -> "DomainFieldBuilder[T]":
        """Start building field expression.

        Args:
            name: Field name

        Returns:
            Field builder
        """
        return DomainFieldBuilder(name, self)

    def and_(self) -> "DomainBuilder[T]":
        """Add AND operator.

        Returns:
            Self for chaining
        """
        self._current_op = "&"
        return self

    def or_(self) -> "DomainBuilder[T]":
        """Add OR operator.

        Returns:
            Self for chaining
        """
        self._current_op = "|"
        return self

    def not_(self) -> "DomainBuilder[T]":
        """Add NOT operator.

        Returns:
            Self for chaining
        """
        self._current_op = "!"
        return self

    def add_leaf(
        self, field: str, operator: Operator, value: Union[T, List[T]]
    ) -> "DomainBuilder[T]":
        """Add leaf node.

        Args:
            field: Field name
            operator: Operator
            value: Value or list of values for in/not in operators

        Returns:
            Self for chaining
        """
        leaf = DomainLeaf[T](field, operator, cast(T, value))
        if self._current_op and self._nodes:
            node = DomainNode[T](self._current_op, [self._nodes[-1], leaf])
            self._nodes[-1] = node
        else:
            self._nodes.append(leaf)
        self._current_op = None
        return self

    def build(self) -> DomainExpression[T]:
        """Build domain expression.

        Returns:
            Domain expression

        Raises:
            ValueError: If no nodes added
        """
        if not self._nodes:
            raise ValueError("No nodes added")
        expr = DomainExpression[T]([])
        expr.root = self._nodes[0]
        return expr


class DomainFieldBuilder(Generic[T]):
    """Builder for field expressions.

    Examples:
        >>> builder = DomainFieldBuilder("age")
        >>> expr = builder.greater_than(18)
        >>> visitor = MongoDomainVisitor()
        >>> mongo_query = expr.accept(visitor)
        >>> {"age": {"$gt": 18}}
    """

    def __init__(self, field: str, parent: DomainBuilder[T]) -> None:
        """Initialize field builder.

        Args:
            field: Field name
            parent: Parent builder
        """
        self.field = field
        self.parent = parent

    def equals(self, value: T) -> DomainBuilder[T]:
        """Field equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "=", value)

    def not_equals(self, value: T) -> DomainBuilder[T]:
        """Field not equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "!=", value)

    def greater_than(self, value: T) -> DomainBuilder[T]:
        """Field greater than value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, ">", value)

    def greater_equals(self, value: T) -> DomainBuilder[T]:
        """Field greater than or equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, ">=", value)

    def less_than(self, value: T) -> DomainBuilder[T]:
        """Field less than value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "<", value)

    def less_equals(self, value: T) -> DomainBuilder[T]:
        """Field less than or equals value.

        Args:
            value: Value to compare

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "<=", value)

    def in_(self, values: List[T]) -> DomainBuilder[T]:
        """Field in values.

        Args:
            values: List of values

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "in", values)

    def not_in(self, values: List[T]) -> DomainBuilder[T]:
        """Field not in values.

        Args:
            values: List of values

        Returns:
            Parent builder
        """
        return self.parent.add_leaf(self.field, "not in", values)
