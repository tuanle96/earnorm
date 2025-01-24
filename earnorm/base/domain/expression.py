"""Domain expressions for query building.

This module provides domain expressions for building complex queries.

Examples:
    >>> expr = DomainExpression([
    ...     ["age", ">", 18],
    ...     "AND",
    ...     ["status", "=", "active"]
    ... ])
    >>> mongo_query = expr.to_mongo()
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, TypeVar, Union, cast

from earnorm.types import DomainOperator, JsonDict

T = TypeVar("T", bound=Union["DomainNode", "DomainLeaf"])
DomainItem = Union[List[Any], str]


class LogicalOperator(str, Enum):
    """Logical operators for combining domain expressions."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class DomainLeaf:
    """Leaf node in domain expression tree.

    Examples:
        >>> leaf = DomainLeaf("age", ">", 18)
        >>> leaf.to_mongo()
        {"age": {"$gt": 18}}
    """

    field: str
    operator: DomainOperator
    value: Any

    def to_mongo(self) -> JsonDict:
        """Convert to MongoDB query.

        Returns:
            MongoDB query dict
        """
        if self.operator == "=":
            return {self.field: self.value}
        elif self.operator == "!=":
            return {self.field: {"$ne": self.value}}
        elif self.operator == ">":
            return {self.field: {"$gt": self.value}}
        elif self.operator == ">=":
            return {self.field: {"$gte": self.value}}
        elif self.operator == "<":
            return {self.field: {"$lt": self.value}}
        elif self.operator == "<=":
            return {self.field: {"$lte": self.value}}
        elif self.operator == "in":
            return {self.field: {"$in": self.value}}
        elif self.operator == "not in":
            return {self.field: {"$nin": self.value}}
        elif self.operator == "like":
            return {self.field: {"$regex": self.value, "$options": "i"}}
        elif self.operator == "ilike":
            return {self.field: {"$regex": self.value, "$options": "i"}}
        elif self.operator == "not like":
            return {self.field: {"$not": {"$regex": self.value, "$options": "i"}}}
        elif self.operator == "not ilike":
            return {self.field: {"$not": {"$regex": self.value, "$options": "i"}}}
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")


@dataclass
class DomainNode:
    """Node in domain expression tree.

    Examples:
        >>> node = DomainNode(
        ...     LogicalOperator.AND,
        ...     [
        ...         DomainLeaf("age", ">", 18),
        ...         DomainLeaf("status", "=", "active")
        ...     ]
        ... )
        >>> node.to_mongo()
        {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    """

    operator: LogicalOperator
    children: List[Union["DomainNode", DomainLeaf]]

    def to_mongo(self) -> JsonDict:
        """Convert to MongoDB query.

        Returns:
            MongoDB query dict
        """
        if self.operator == LogicalOperator.AND:
            return {"$and": [child.to_mongo() for child in self.children]}
        elif self.operator == LogicalOperator.OR:
            return {"$or": [child.to_mongo() for child in self.children]}
        elif self.operator == LogicalOperator.NOT:
            return {"$not": self.children[0].to_mongo()}
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")


class DomainExpression:
    """Domain expression for building complex queries.

    Examples:
        >>> expr = DomainExpression([
        ...     ["age", ">", 18],
        ...     "AND",
        ...     ["status", "=", "active"]
        ... ])
        >>> expr.to_mongo()
        {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
    """

    def __init__(self, domain: List[DomainItem]) -> None:
        """Initialize domain expression.

        Args:
            domain: Domain expression list
        """
        self.domain = domain
        self.root = self._parse(domain)

    def _parse(
        self, domain: List[DomainItem], pos: int = 0
    ) -> Optional[Union[DomainNode, DomainLeaf]]:
        """Parse domain expression list into tree.

        Args:
            domain: Domain expression list
            pos: Current position in list

        Returns:
            Root node of expression tree
        """
        if not domain:
            return None

        # Parse first expression
        if isinstance(domain[pos], list):
            operator = domain[pos][1]
            if not isinstance(operator, str):
                raise ValueError(f"Invalid operator type: {type(operator)}")
            left = DomainLeaf(
                field=domain[pos][0],
                operator=cast(DomainOperator, operator),  # Safe cast after type check
                value=domain[pos][2],
            )
        else:
            left = self._parse(domain, pos + 1)

        # Check if we're done
        if pos + 1 >= len(domain):
            return left

        # Parse operator
        if not isinstance(domain[pos + 1], str):
            return left

        op = LogicalOperator(domain[pos + 1])

        # Parse right side
        if pos + 2 >= len(domain):
            raise ValueError("Missing right operand")

        if isinstance(domain[pos + 2], list):
            operator = domain[pos + 2][1]
            if not isinstance(operator, str):
                raise ValueError(f"Invalid operator type: {type(operator)}")
            right = DomainLeaf(
                field=domain[pos + 2][0],
                operator=cast(DomainOperator, operator),  # Safe cast after type check
                value=domain[pos + 2][2],
            )
        else:
            right = self._parse(domain, pos + 3)

        # Create node with type-safe children
        children = [left] if left else []
        if right:
            children.append(right)

        return DomainNode(op, children)

    def to_mongo(self) -> JsonDict:
        """Convert to MongoDB query.

        Returns:
            MongoDB query dict
        """
        if not self.root:
            return {}
        return self.root.to_mongo()
