"""Aggregate operation implementation.

This module provides base implementation for aggregate operations.
All database-specific aggregate implementations should inherit from this class.

Examples:
    >>> class MongoAggregate(BaseAggregate[User]):
    ...     def to_pipeline(self) -> list[JsonDict]:
    ...         pipeline = []
    ...         if self._group_fields:
    ...             pipeline.append({
    ...                 "$group": {
    ...                     "_id": {field: f"${field}" for field in self._group_fields},
    ...                     **self._aggregates
    ...                 }
    ...             })
    ...         return pipeline
"""

from typing import Any, Dict, List, Optional, TypeVar, Union

from earnorm.base.database.query.core.operations.base import BaseOperation
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class BaseAggregate(BaseOperation[ModelT], AggregateProtocol[ModelT]):
    """Base class for aggregate operations.

    This class provides common functionality for aggregate operations.
    Database-specific aggregate implementations should inherit from this class.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize aggregate operation."""
        super().__init__()
        self._group_fields: List[str] = []
        self._having: Optional[Union[List[Any], JsonDict]] = None
        self._aggregates: Dict[str, Any] = {}

    def group_by(self, *fields: str) -> "BaseAggregate[ModelT]":
        """Group results by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        self._group_fields.extend(fields)
        return self

    def having(self, domain: Union[List[Any], JsonDict]) -> "BaseAggregate[ModelT]":
        """Add having conditions.

        Args:
            domain: Having conditions

        Returns:
            Self for chaining
        """
        self._having = domain
        return self

    def count(
        self, field: str = "*", alias: Optional[str] = None
    ) -> "BaseAggregate[ModelT]":
        """Count records.

        Args:
            field: Field to count
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"count_{field}"
        self._aggregates[alias] = {"$count": field if field != "*" else ""}
        return self

    def sum(self, field: str, alias: Optional[str] = None) -> "BaseAggregate[ModelT]":
        """Sum field values.

        Args:
            field: Field to sum
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"sum_{field}"
        self._aggregates[alias] = {"$sum": f"${field}"}
        return self

    def avg(self, field: str, alias: Optional[str] = None) -> "BaseAggregate[ModelT]":
        """Average field values.

        Args:
            field: Field to average
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"avg_{field}"
        self._aggregates[alias] = {"$avg": f"${field}"}
        return self

    def min(self, field: str, alias: Optional[str] = None) -> "BaseAggregate[ModelT]":
        """Get minimum field value.

        Args:
            field: Field to get minimum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"min_{field}"
        self._aggregates[alias] = {"$min": f"${field}"}
        return self

    def max(self, field: str, alias: Optional[str] = None) -> "BaseAggregate[ModelT]":
        """Get maximum field value.

        Args:
            field: Field to get maximum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"max_{field}"
        self._aggregates[alias] = {"$max": f"${field}"}
        return self

    def validate(self) -> None:
        """Validate aggregate configuration.

        Raises:
            ValueError: If aggregate configuration is invalid
        """
        if not self._group_fields and not self._aggregates:
            raise ValueError("No grouping fields or aggregate functions specified")

    @property
    def group_fields(self) -> List[str]:
        """Get group fields.

        Returns:
            List of fields to group by
        """
        return self._group_fields

    @property
    def having_conditions(self) -> Optional[Union[List[Any], JsonDict]]:
        """Get having conditions.

        Returns:
            Having conditions
        """
        return self._having

    @property
    def aggregates(self) -> Dict[str, Any]:
        """Get aggregate functions.

        Returns:
            Dictionary of aggregate functions
        """
        return self._aggregates
