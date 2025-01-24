"""Domain expression converters.

This module provides interfaces and implementations for converting domain expressions
to different database query formats.

Examples:
    >>> expr = DomainExpression([["age", ">", 18]])
    >>> mongo_converter = MongoConverter()
    >>> mongo_query = mongo_converter.convert(expr)
    >>> {"age": {"$gt": 18}}

    >>> postgres_converter = PostgresConverter()
    >>> postgres_query = postgres_converter.convert(expr)
    >>> "age > 18"
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from earnorm.base.domain.expression import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
    LogicalOperator,
)
from earnorm.types import DomainOperator, JsonDict

T = TypeVar("T")


class DomainConverter(ABC, Generic[T]):
    """Base class for domain expression converters."""

    @abstractmethod
    def convert(self, expr: DomainExpression) -> T:
        """Convert domain expression to database query.

        Args:
            expr: Domain expression to convert

        Returns:
            Database-specific query format
        """
        pass

    @abstractmethod
    def convert_leaf(self, leaf: DomainLeaf) -> T:
        """Convert leaf node to database query.

        Args:
            leaf: Leaf node to convert

        Returns:
            Database-specific query format
        """
        pass

    @abstractmethod
    def convert_node(self, node: DomainNode) -> T:
        """Convert node to database query.

        Args:
            node: Node to convert

        Returns:
            Database-specific query format
        """
        pass


class MongoConverter(DomainConverter[JsonDict]):
    """Converter for MongoDB queries."""

    def convert(self, expr: DomainExpression) -> JsonDict:
        """Convert domain expression to MongoDB query.

        Args:
            expr: Domain expression to convert

        Returns:
            MongoDB query dict
        """
        if not expr.root:
            return {}
        return (
            self.convert_node(expr.root)
            if isinstance(expr.root, DomainNode)
            else self.convert_leaf(expr.root)
        )

    def convert_leaf(self, leaf: DomainLeaf) -> JsonDict:
        """Convert leaf node to MongoDB query.

        Args:
            leaf: Leaf node to convert

        Returns:
            MongoDB query dict
        """
        operator: DomainOperator = leaf.operator  # Type annotation for clarity

        if operator == "=":
            return {leaf.field: leaf.value}
        elif operator == "!=":
            return {leaf.field: {"$ne": leaf.value}}
        elif operator == ">":
            return {leaf.field: {"$gt": leaf.value}}
        elif operator == ">=":
            return {leaf.field: {"$gte": leaf.value}}
        elif operator == "<":
            return {leaf.field: {"$lt": leaf.value}}
        elif operator == "<=":
            return {leaf.field: {"$lte": leaf.value}}
        elif operator == "in":
            return {leaf.field: {"$in": leaf.value}}
        elif operator == "not in":
            return {leaf.field: {"$nin": leaf.value}}
        elif operator in ("like", "ilike", "=like", "=ilike"):
            return {leaf.field: {"$regex": leaf.value, "$options": "i"}}
        elif operator in ("not like", "not ilike"):
            return {leaf.field: {"$not": {"$regex": leaf.value, "$options": "i"}}}
        elif operator == "contains":
            return {leaf.field: {"$regex": f".*{leaf.value}.*", "$options": "i"}}
        elif operator == "not contains":
            return {
                leaf.field: {"$not": {"$regex": f".*{leaf.value}.*", "$options": "i"}}
            }
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def convert_node(self, node: DomainNode) -> JsonDict:
        """Convert node to MongoDB query.

        Args:
            node: Node to convert

        Returns:
            MongoDB query dict
        """
        if node.operator == LogicalOperator.AND:
            return {
                "$and": [
                    (
                        self.convert_node(child)
                        if isinstance(child, DomainNode)
                        else self.convert_leaf(child)
                    )
                    for child in node.children
                ]
            }
        elif node.operator == LogicalOperator.OR:
            return {
                "$or": [
                    (
                        self.convert_node(child)
                        if isinstance(child, DomainNode)
                        else self.convert_leaf(child)
                    )
                    for child in node.children
                ]
            }
        elif node.operator == LogicalOperator.NOT:
            child = node.children[0]
            return {
                "$not": (
                    self.convert_node(child)
                    if isinstance(child, DomainNode)
                    else self.convert_leaf(child)
                )
            }
        else:
            raise ValueError(f"Unsupported operator: {node.operator}")


class PostgresConverter(DomainConverter[str]):
    """Converter for PostgreSQL queries."""

    def convert(self, expr: DomainExpression) -> str:
        """Convert domain expression to PostgreSQL query.

        Args:
            expr: Domain expression to convert

        Returns:
            PostgreSQL WHERE clause
        """
        if not expr.root:
            return ""
        return (
            self.convert_node(expr.root)
            if isinstance(expr.root, DomainNode)
            else self.convert_leaf(expr.root)
        )

    def convert_leaf(self, leaf: DomainLeaf) -> str:
        """Convert leaf node to PostgreSQL query.

        Args:
            leaf: Leaf node to convert

        Returns:
            PostgreSQL WHERE clause
        """
        operator: DomainOperator = leaf.operator  # Type annotation for clarity
        value = self._format_value(leaf.value)

        if operator == "=":
            return f"{leaf.field} = {value}"
        elif operator == "!=":
            return f"{leaf.field} != {value}"
        elif operator == ">":
            return f"{leaf.field} > {value}"
        elif operator == ">=":
            return f"{leaf.field} >= {value}"
        elif operator == "<":
            return f"{leaf.field} < {value}"
        elif operator == "<=":
            return f"{leaf.field} <= {value}"
        elif operator == "in":
            values = ", ".join(map(self._format_value, leaf.value))
            return f"{leaf.field} IN ({values})"
        elif operator == "not in":
            values = ", ".join(map(self._format_value, leaf.value))
            return f"{leaf.field} NOT IN ({values})"
        elif operator in ("like", "=like"):
            return f"{leaf.field} LIKE {value}"
        elif operator in ("ilike", "=ilike"):
            return f"{leaf.field} ILIKE {value}"
        elif operator == "not like":
            return f"{leaf.field} NOT LIKE {value}"
        elif operator == "not ilike":
            return f"{leaf.field} NOT ILIKE {value}"
        elif operator == "contains":
            return f"{leaf.field} ILIKE '%' || {value} || '%'"
        elif operator == "not contains":
            return f"{leaf.field} NOT ILIKE '%' || {value} || '%'"
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def convert_node(self, node: DomainNode) -> str:
        """Convert node to PostgreSQL query.

        Args:
            node: Node to convert

        Returns:
            PostgreSQL WHERE clause
        """
        if node.operator == LogicalOperator.AND:
            clauses = [
                (
                    self.convert_node(child)
                    if isinstance(child, DomainNode)
                    else self.convert_leaf(child)
                )
                for child in node.children
            ]
            return f"({' AND '.join(clauses)})"
        elif node.operator == LogicalOperator.OR:
            clauses = [
                (
                    self.convert_node(child)
                    if isinstance(child, DomainNode)
                    else self.convert_leaf(child)
                )
                for child in node.children
            ]
            return f"({' OR '.join(clauses)})"
        elif node.operator == LogicalOperator.NOT:
            child = node.children[0]
            clause = (
                self.convert_node(child)
                if isinstance(child, DomainNode)
                else self.convert_leaf(child)
            )
            return f"NOT ({clause})"
        else:
            raise ValueError(f"Unsupported operator: {node.operator}")

    def _format_value(self, value: Any) -> str:
        """Format value for PostgreSQL query.

        Args:
            value: Value to format

        Returns:
            Formatted value string
        """
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return f"'{value}'"  # Basic escaping, should use parameterized queries in production
        else:
            return f"'{str(value)}'"
