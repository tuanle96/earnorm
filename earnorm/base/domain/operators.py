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
from typing import Generic, Tuple, TypeVar

from earnorm.types import JsonDict, ValueType

T = TypeVar("T", bound=ValueType)
RangeType = Tuple[ValueType, ValueType]


class CustomOperator(Generic[T], ABC):
    """Base class for custom operators.

    Examples:
        >>> class ContainsOperator(CustomOperator[str]):
        ...     name = "contains"
        ...
        ...     def to_mongo(self, field, value):
        ...         return {field: {"$regex": f".*{value}.*"}}
    """

    name: str

    @abstractmethod
    def to_mongo(self, field: str, value: T) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        pass

    @abstractmethod
    def to_postgres(self, field: str, value: T) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        pass


class ContainsOperator(CustomOperator[str]):
    """Contains operator for string fields."""

    name = "contains"

    def to_mongo(self, field: str, value: str) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f".*{value}.*", "$options": "i"}}

    def to_postgres(self, field: str, value: str) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '%{value}%'"


class StartsWithOperator(CustomOperator[str]):
    """Starts with operator for string fields."""

    name = "starts_with"

    def to_mongo(self, field: str, value: str) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f"^{value}", "$options": "i"}}

    def to_postgres(self, field: str, value: str) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '{value}%'"


class EndsWithOperator(CustomOperator[str]):
    """Ends with operator for string fields."""

    name = "ends_with"

    def to_mongo(self, field: str, value: str) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: Field value

        Returns:
            MongoDB query dict
        """
        return {field: {"$regex": f"{value}$", "$options": "i"}}

    def to_postgres(self, field: str, value: str) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: Field value

        Returns:
            PostgreSQL condition
        """
        return f"{field} ILIKE '%{value}'"


class BaseRangeOperator(ABC):
    """Base class for range operators."""

    name: str

    @abstractmethod
    def to_mongo(self, field: str, value: RangeType) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            MongoDB query dict
        """
        pass

    @abstractmethod
    def to_postgres(self, field: str, value: RangeType) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            PostgreSQL condition
        """
        pass


class RangeOperator(BaseRangeOperator):
    """Range operator for numeric fields."""

    name = "range"

    def to_mongo(self, field: str, value: RangeType) -> JsonDict:
        """Convert to MongoDB query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            MongoDB query dict
        """
        min_val, max_val = value
        return {
            field: {
                "$gte": min_val,
                "$lte": max_val,
            }
        }

    def to_postgres(self, field: str, value: RangeType) -> str:
        """Convert to PostgreSQL query.

        Args:
            field: Field name
            value: (min, max) tuple

        Returns:
            PostgreSQL condition
        """
        min_val, max_val = value
        return f"{field} BETWEEN {min_val} AND {max_val}"
