"""Window operation interface.

This module defines the interface for window operations.
All database-specific window implementations must implement this interface.

Examples:
    >>> # Using window functions
    >>> query.select(
    ...     User.name,
    ...     row_number().over(partition_by=[User.country]).as_("rank"),
    ...     lag(User.salary).over(order_by=[User.hire_date]).as_("prev_salary")
    ... )
"""

from abc import abstractmethod
from typing import Any, List, Optional, TypeVar

from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class WindowProtocol(OperationProtocol[ModelT]):
    """Protocol for window operations."""

    @abstractmethod
    def over(
        self,
        partition_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
    ) -> "WindowProtocol[ModelT]":
        """Set window clause.

        Args:
            partition_by: Fields to partition by
            order_by: Fields to order by

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def as_(self, alias: str) -> str:
        """Set alias for window expression.

        Args:
            alias: Alias name

        Returns:
            Window expression with alias
        """
        ...

    @abstractmethod
    def row_number(self) -> "WindowProtocol[ModelT]":
        """ROW_NUMBER() window function.

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def rank(self) -> "WindowProtocol[ModelT]":
        """RANK() window function.

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def dense_rank(self) -> "WindowProtocol[ModelT]":
        """DENSE_RANK() window function.

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def first_value(self, field: str) -> "WindowProtocol[ModelT]":
        """FIRST_VALUE() window function.

        Args:
            field: Field to get first value of

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def last_value(self, field: str) -> "WindowProtocol[ModelT]":
        """LAST_VALUE() window function.

        Args:
            field: Field to get last value of

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def lag(
        self, field: str, offset: int = 1, default: Any = None
    ) -> "WindowProtocol[ModelT]":
        """LAG() window function.

        Args:
            field: Field to lag
            offset: Number of rows to lag
            default: Default value if no row exists

        Returns:
            Window expression
        """
        ...

    @abstractmethod
    def lead(
        self, field: str, offset: int = 1, default: Any = None
    ) -> "WindowProtocol[ModelT]":
        """LEAD() window function.

        Args:
            field: Field to lead
            offset: Number of rows to lead
            default: Default value if no row exists

        Returns:
            Window expression
        """
        ...
