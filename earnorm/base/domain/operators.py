"""Custom domain operators.

This module provides base class and implementations for custom domain operators.

Examples:
    >>> class ContainsOperator(CustomOperator):
    ...     name = "contains"
    ...
    ...     def to_mongo(self, field, value):
    ...         return {field: {"$regex": f".*{value}.*"}}
"""

from abc import ABC, abstractmethod
from typing import Any

from earnorm.types import JsonDict


class CustomOperator(ABC):
    """Base class for custom operators.

    Examples:
        >>> class ContainsOperator(CustomOperator):
        ...     name = "contains"
        ...
        ...     def to_mongo(self, field, value):
        ...         return {field: {"$regex": f".*{value}.*"}}
    """

    name: str

    @abstractmethod
    def to_mongo(self, field: str, value: Any) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        pass

    @abstractmethod
    def to_postgres(self, field: str, value: Any) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        pass


class ContainsOperator(CustomOperator):
    """Operator for substring matching.

    Examples:
        >>> op = ContainsOperator()
        >>> op.to_mongo("name", "John")
        {"name": {"$regex": ".*John.*"}}
        >>> op.to_postgres("name", "John")
        "name LIKE '%John%'"
    """

    name = "contains"

    def to_mongo(self, field: str, value: Any) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f".*{value}.*", "$options": "i"}}

    def to_postgres(self, field: str, value: Any) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '%{value}%'"


class StartsWithOperator(CustomOperator):
    """Operator for prefix matching.

    Examples:
        >>> op = StartsWithOperator()
        >>> op.to_mongo("name", "John")
        {"name": {"$regex": "^John.*"}}
        >>> op.to_postgres("name", "John")
        "name LIKE 'John%'"
    """

    name = "starts_with"

    def to_mongo(self, field: str, value: Any) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f"^{value}.*", "$options": "i"}}

    def to_postgres(self, field: str, value: Any) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '{value}%'"


class EndsWithOperator(CustomOperator):
    """Operator for suffix matching.

    Examples:
        >>> op = EndsWithOperator()
        >>> op.to_mongo("name", "son")
        {"name": {"$regex": ".*son$"}}
        >>> op.to_postgres("name", "son")
        "name LIKE '%son'"
    """

    name = "ends_with"

    def to_mongo(self, field: str, value: Any) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f".*{value}$", "$options": "i"}}

    def to_postgres(self, field: str, value: Any) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '%{value}'"


class RangeOperator(CustomOperator):
    """Operator for range queries.

    Examples:
        >>> op = RangeOperator()
        >>> op.to_mongo("age", (18, 30))
        {"age": {"$gte": 18, "$lte": 30}}
        >>> op.to_postgres("age", (18, 30))
        "age BETWEEN 18 AND 30"
    """

    name = "range"

    def to_mongo(self, field: str, value: tuple[Any, Any]) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            MongoDB query dict
        """
        min_val, max_val = value
        return {field: {"$gte": min_val, "$lte": max_val}}

    def to_postgres(self, field: str, value: tuple[Any, Any]) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            PostgreSQL condition
        """
        min_val, max_val = value
        return f"{field} BETWEEN {min_val} AND {max_val}"
