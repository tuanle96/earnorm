"""Domain expression converters.

This module provides base classes for converting domain expressions to
database-specific formats.

Examples:
    >>> expr = DomainExpression([
    ...     ("age", ">", 18),
    ...     "&",
    ...     ("status", "=", "active")
    ... ])
    >>> converter = MongoConverter()
    >>> mongo_query = converter.convert(expr)
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

from abc import ABC, abstractmethod
from typing import Dict, Generic, TypeVar, Union

from earnorm.base.domain.expression import DomainLeaf, DomainNode
from earnorm.types import JsonDict, ValueType

T = TypeVar("T")


class DomainConverter(Generic[T], ABC):
    """Base class for domain expression converters.

    This class defines the interface that all database-specific converters must implement.
    It provides methods for converting domain expressions to database-specific formats.

    Args:
        T: Type of converted expression
    """

    @abstractmethod
    def convert_leaf(self, leaf: DomainLeaf[ValueType]) -> T:
        """Convert leaf node.

        Args:
            leaf: Leaf node to convert

        Returns:
            Database-specific format
        """
        pass

    @abstractmethod
    def convert_node(self, node: DomainNode[ValueType]) -> T:
        """Convert logical node.

        Args:
            node: Logical node to convert

        Returns:
            Database-specific format
        """
        pass

    def convert(self, expr: Union[DomainLeaf[ValueType], DomainNode[ValueType]]) -> T:
        """Convert domain expression.

        Args:
            expr: Domain expression to convert

        Returns:
            Database-specific format

        Raises:
            ValueError: If expression is invalid
        """
        expr.validate()
        if isinstance(expr, DomainLeaf):
            return self.convert_leaf(expr)
        return self.convert_node(expr)


class JsonConverter(DomainConverter[JsonDict]):
    """Base class for JSON-based converters.

    This class provides common functionality for converters that produce
    JSON-compatible dictionaries.
    """

    _OPERATOR_MAP: Dict[str, str | None] = {}
    _LOGICAL_MAP: Dict[str, str] = {}

    def convert_leaf(self, leaf: DomainLeaf[ValueType]) -> JsonDict:
        """Convert leaf node to JSON dict.

        Args:
            leaf: Leaf node to convert

        Returns:
            JSON-compatible dict

        Raises:
            ValueError: If operator is not supported
        """
        if leaf.operator not in self._OPERATOR_MAP:
            raise ValueError(f"Operator {leaf.operator} not supported")

        op = self._OPERATOR_MAP[leaf.operator]
        if op is None:
            # Direct value comparison
            return {leaf.field: leaf.value}

        return {leaf.field: {op: leaf.value}}

    def convert_node(self, node: DomainNode[ValueType]) -> JsonDict:
        """Convert logical node to JSON dict.

        Args:
            node: Logical node to convert

        Returns:
            JSON-compatible dict

        Raises:
            ValueError: If operator is not supported
        """
        if node.operator not in self._LOGICAL_MAP:
            raise ValueError(f"Operator {node.operator} not supported")

        op = self._LOGICAL_MAP[node.operator]
        if op == "$not":
            # NOT only takes one operand
            if len(node.children) != 1:
                raise ValueError("NOT operator requires exactly one operand")
            return {op: self.convert(node.children[0])}

        # AND/OR take a list of operands
        return {op: [self.convert(child) for child in node.children]}
