"""MongoDB domain expression converter.

This module provides a visitor for converting domain expressions to MongoDB queries.

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

from typing import Dict, Optional, TypeVar

from earnorm.base.domain.converter import JsonConverter
from earnorm.base.domain.expression import DomainLeaf, DomainNode, DomainVisitor
from earnorm.types import JsonDict

T = TypeVar("T")


class MongoConverter(JsonConverter, DomainVisitor):
    """MongoDB domain expression converter.

    This class implements a visitor pattern to convert domain expressions
    into MongoDB query dictionaries.

    Attributes:
        _OPERATOR_MAP: Dict mapping domain operators to MongoDB operators.
            Keys are domain operator strings, values are MongoDB operator strings or None.
        _LOGICAL_MAP: Dict mapping domain logical operators to MongoDB logical operators.
            Keys are domain logical operator strings, values are MongoDB logical operator strings.
    """

    _OPERATOR_MAP: Dict[str, Optional[str]] = {
        "=": None,  # Direct value
        "!=": "$ne",
        ">": "$gt",
        ">=": "$gte",
        "<": "$lt",
        "<=": "$lte",
        "in": "$in",
        "not in": "$nin",
    }

    _LOGICAL_MAP: Dict[str, str] = {
        "&": "$and",
        "|": "$or",
        "!": "$not",
    }

    def visit_leaf(self, leaf: DomainLeaf[T]) -> JsonDict:
        """Visit leaf node.

        Args:
            leaf: Leaf node to visit

        Returns:
            MongoDB query dict

        Raises:
            ValueError: If leaf node is invalid
        """
        leaf.validate()
        mongo_op = self._OPERATOR_MAP[leaf.operator]

        if mongo_op is None:
            # Direct value comparison
            return {leaf.field: leaf.value}

        return {leaf.field: {mongo_op: leaf.value}}

    def visit_node(self, node: DomainNode[T]) -> JsonDict:
        """Visit logical node.

        Args:
            node: Logical node to visit

        Returns:
            MongoDB query dict

        Raises:
            ValueError: If node is invalid or NOT operator has wrong number of operands
        """
        node.validate()
        mongo_op = self._LOGICAL_MAP[node.operator]

        if mongo_op == "$not":
            # NOT only takes one operand
            if len(node.children) != 1:
                raise ValueError("NOT operator requires exactly one operand")
            return {mongo_op: node.children[0].accept(self)}

        # AND/OR take a list of operands
        return {mongo_op: [child.accept(self) for child in node.children]}
