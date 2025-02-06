"""Aggregate operation interface.

This module defines the interface for aggregate operations.
All database-specific aggregate implementations must implement this interface.

Examples:
    >>> # Using aggregate interface
    >>> query.group_by(User.country)
    >>> query.having(count("*") > 10)
    >>> query.aggregate(
    ...     count("*").as_("total"),
    ...     avg(User.age).as_("avg_age")
    ... )
"""

from abc import abstractmethod
from typing import Any, List, Optional, TypeVar, Union

from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class AggregateProtocol(OperationProtocol[ModelT]):
    """Protocol for aggregate operations."""

    @abstractmethod
    def group_by(self, *fields: str) -> "AggregateProtocol[ModelT]":
        """Group results by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def having(self, domain: Union[List[Any], JsonDict]) -> "AggregateProtocol[ModelT]":
        """Add having conditions.

        Args:
            domain: Having conditions

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def count(
        self, field: str = "*", alias: Optional[str] = None
    ) -> "AggregateProtocol[ModelT]":
        """Count records.

        Args:
            field: Field to count
            alias: Result alias

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def sum(
        self, field: str, alias: Optional[str] = None
    ) -> "AggregateProtocol[ModelT]":
        """Sum field values.

        Args:
            field: Field to sum
            alias: Result alias

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def avg(
        self, field: str, alias: Optional[str] = None
    ) -> "AggregateProtocol[ModelT]":
        """Average field values.

        Args:
            field: Field to average
            alias: Result alias

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def min(
        self, field: str, alias: Optional[str] = None
    ) -> "AggregateProtocol[ModelT]":
        """Get minimum field value.

        Args:
            field: Field to get minimum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def max(
        self, field: str, alias: Optional[str] = None
    ) -> "AggregateProtocol[ModelT]":
        """Get maximum field value.

        Args:
            field: Field to get maximum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        ...

    def validate(self) -> None:
        """Validate aggregate configuration.

        Raises:
            ValueError: If aggregate configuration is invalid
        """
        ...

    def get_pipeline_stages(self) -> List[JsonDict]:
        """Get MongoDB aggregation pipeline stages for this aggregation.

        Returns:
            List[JsonDict]: List of pipeline stages
        """
        ...
