"""Domain expressions for query building.

This module provides domain expressions for building complex queries.
It uses visitor pattern for database-specific conversions.

Examples:
    >>> expr = DomainExpression([
    ...     ("age", ">", 18),
    ...     "&",
    ...     ("status", "=", "active")
    ... ])
    >>> visitor = MongoDomainVisitor()
    >>> mongo_query = expr.accept(visitor)
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, List, Literal, Tuple, TypeVar, Union

T = TypeVar("T")  # Value type
Operator = Literal["=", ">", "<", ">=", "<=", "!=", "in", "not in"]
LogicalOp = Literal["&", "|", "!"]


class DomainVisitor(ABC):
    """Visitor for domain expressions."""

    @abstractmethod
    def visit_leaf(self, leaf: "DomainLeaf[T]") -> Any:
        """Visit leaf node.

        Args:
            leaf: Leaf node to visit

        Returns:
            Database-specific query format
        """
        pass

    @abstractmethod
    def visit_node(self, node: "DomainNode[T]") -> Any:
        """Visit logical node.

        Args:
            node: Logical node to visit

        Returns:
            Database-specific query format
        """
        pass


@dataclass
class DomainLeaf(Generic[T]):
    """Leaf node in domain expression tree.

    Examples:
        >>> leaf = DomainLeaf("age", ">", 18)
        >>> visitor = MongoDomainVisitor()
        >>> leaf.accept(visitor)
        {"age": {"$gt": 18}}
    """

    field: str
    operator: Operator
    value: T

    def accept(self, visitor: DomainVisitor) -> Any:
        """Accept visitor.

        Args:
            visitor: Domain visitor

        Returns:
            Database-specific query format
        """
        return visitor.visit_leaf(self)

    def validate(self) -> None:
        """Validate leaf node.

        Raises:
            ValueError: If node is invalid
        """
        if not self.field:
            raise ValueError("Field name is required")
        if not self.operator:
            raise ValueError("Operator is required")


@dataclass
class DomainNode(Generic[T]):
    """Logical node in domain expression tree.

    Examples:
        >>> node = DomainNode(
        ...     "&",
        ...     [DomainLeaf("age", ">", 18), DomainLeaf("status", "=", "active")]
        ... )
        >>> visitor = MongoDomainVisitor()
        >>> node.accept(visitor)
        {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    """

    operator: LogicalOp
    children: List[Union["DomainNode[T]", "DomainLeaf[T]"]]

    def accept(self, visitor: DomainVisitor) -> Any:
        """Accept visitor.

        Args:
            visitor: Domain visitor

        Returns:
            Database-specific query format
        """
        return visitor.visit_node(self)

    def validate(self) -> None:
        """Validate logical node.

        Raises:
            ValueError: If node is invalid
        """
        if not self.operator:
            raise ValueError("Operator is required")
        if not self.children:
            raise ValueError("Children are required")
        for child in self.children:
            child.validate()


class DomainExpression(Generic[T]):
    """Domain expression for building complex queries.

    This class represents a domain expression tree that can be converted
    to different database query formats using visitors.

    Examples:
        >>> expr = DomainExpression([
        ...     ("age", ">", 18),
        ...     "&",
        ...     ("status", "=", "active")
        ... ])
        >>> visitor = MongoDomainVisitor()
        >>> expr.accept(visitor)
        {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    """

    def __init__(self, domain: List[Union[Tuple[str, Operator, T], LogicalOp]]) -> None:
        """Initialize domain expression.

        Args:
            domain: Domain expression in list format
        """
        self.root = self._parse(domain)

    def accept(self, visitor: DomainVisitor) -> Any:
        """Accept visitor.

        Args:
            visitor: Domain visitor

        Returns:
            Database-specific query format
        """
        return self.root.accept(visitor)

    def validate(self) -> None:
        """Validate expression tree.

        Raises:
            ValueError: If tree is invalid
        """
        self.root.validate()

    def _parse(
        self, domain: List[Union[Tuple[str, Operator, T], LogicalOp]]
    ) -> Union[DomainNode[T], DomainLeaf[T]]:
        """Parse domain list into expression tree.

        Args:
            domain: Domain expression in list format

        Returns:
            Root node of expression tree

        Raises:
            ValueError: If domain list is invalid
        """
        if not domain:
            raise ValueError("Domain list is empty")

        # Handle single leaf case
        if len(domain) == 1:
            item = domain[0]
            if isinstance(item, tuple):
                field, op, value = item
                return DomainLeaf[T](field, op, value)
            raise ValueError("Invalid domain format")

        # Find logical operator
        for i, item in enumerate(domain):
            if isinstance(item, str) and item in ("&", "|", "!"):
                # Split domain list at operator
                left = domain[:i]
                right = domain[i + 1 :]

                # Create leaf nodes
                left_node = self._parse(left)
                right_node = self._parse(right)

                # Create logical node
                return DomainNode[T](item, [left_node, right_node])

        # No logical operator found, must be a leaf
        if isinstance(domain[0], tuple):
            field, op, value = domain[0]
            return DomainLeaf[T](field, op, value)
        raise ValueError("Invalid domain format")
