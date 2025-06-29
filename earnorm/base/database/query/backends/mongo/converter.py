"""MongoDB domain converter implementation.

This module provides MongoDB-specific implementation for converting domain expressions
to MongoDB query format.

Examples:
    >>> converter = MongoConverter()
    >>> domain = [("age", ">", 18), "&", ("status", "=", "active")]
    >>> query = converter.convert(domain)
    >>> # Result: {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

import logging
from typing import Any, Protocol

from bson.objectid import ObjectId

from earnorm.base.database.query.interfaces.domain import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
)
from earnorm.types import JsonDict


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class MongoConverter:
    """MongoDB domain converter implementation.

    This class provides MongoDB-specific implementation for converting domain expressions
    to MongoDB query format.
    """

    logger: LoggerProtocol = logging.getLogger(__name__)

    # Mapping of domain operators to MongoDB operators
    OPERATOR_MAP = {
        "=": None,  # Direct value comparison
        "!=": "$ne",
        ">": "$gt",
        ">=": "$gte",
        "<": "$lt",
        "<=": "$lte",
        "in": "$in",
        "not in": "$nin",
        "like": "$regex",
        "ilike": "$regex",
        "not like": "$not",
        "not ilike": "$not",
        "is null": "$exists",
        "is not null": "$exists",
    }

    # Mapping of logical operators to MongoDB operators
    LOGICAL_MAP = {
        "&": "$and",
        "|": "$or",
        "!": "$not",
    }

    def convert(self, domain: list[Any] | JsonDict) -> JsonDict:
        """Convert domain to MongoDB query format.

        Args:
            domain: Domain expression or raw MongoDB query

        Returns:
            MongoDB query format
        """
        if isinstance(domain, dict):
            # Raw MongoDB query
            return domain

        # Convert domain list to expression tree
        expr = DomainExpression(domain)  # type: ignore
        if expr.root is None:
            return {}
        return self.convert_node(expr.root)

    def convert_node(self, node: DomainNode | DomainLeaf) -> JsonDict:
        """Convert domain node to MongoDB query format.

        Args:
            node: Domain node

        Returns:
            MongoDB query format
        """
        if isinstance(node, DomainLeaf):
            return self.convert_leaf(node)
        return self.convert_logical(node)

    def convert_leaf(self, leaf: DomainLeaf) -> JsonDict:
        """Convert domain leaf to MongoDB query format.

        Args:
            leaf: Domain leaf

        Returns:
            MongoDB query format
        """
        # Convert id field to _id for MongoDB
        field = "_id" if leaf.field == "id" else leaf.field
        operator = leaf.operator
        value = leaf.value

        # Convert ObjectId if field is _id
        if field == "_id":
            try:
                if operator == "=":
                    value = ObjectId(value)
                elif operator == "in":
                    value = [ObjectId(v) for v in value]
            except Exception as e:
                self.logger.warning(f"Failed to convert to ObjectId: {e}")
                # Keep original value if conversion fails
                pass

        # Handle special cases
        if operator == "=":
            return {field: value}
        elif operator == "is null":
            return {field: {"$exists": False}}
        elif operator == "is not null":
            return {field: {"$exists": True}}
        elif operator in ("like", "ilike"):
            flags = "i" if operator == "ilike" else ""
            pattern = str(value).replace("%", ".*")
            return {field: {"$regex": pattern, "$options": flags}}
        elif operator in ("not like", "not ilike"):
            flags = "i" if operator == "not ilike" else ""
            pattern = str(value).replace("%", ".*")
            return {field: {"$not": {"$regex": pattern, "$options": flags}}}

        # Handle normal operators
        mongo_op = self.OPERATOR_MAP.get(operator)
        if mongo_op is None:
            raise ValueError(f"Unsupported operator: {operator}")

        return {field: {mongo_op: value}}

    def convert_logical(self, node: DomainNode) -> JsonDict:
        """Convert logical node to MongoDB query format.

        Args:
            node: Logical node

        Returns:
            MongoDB query format
        """
        operator = node.operator
        operands = node.operands

        # Get MongoDB operator
        mongo_op = self.LOGICAL_MAP.get(operator)
        if mongo_op is None:
            raise ValueError(f"Unsupported logical operator: {operator}")

        # Convert operands
        if operator == "!":
            # NOT operator takes single operand
            if len(operands) != 1:
                raise ValueError("NOT operator requires exactly one operand")
            return {mongo_op: self.convert_node(operands[0])}

        # AND/OR operators take multiple operands
        return {mongo_op: [self.convert_node(op) for op in operands]}
