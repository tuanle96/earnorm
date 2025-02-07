"""Window operation implementation.

This module provides the window operation class for performing window function queries.
It supports various window functions and specifications:

- Ranking functions (row_number, rank, dense_rank)
- Aggregate functions (sum, avg, min, max)
- Frame specifications (rows, range)
- Partition by fields
- Order by fields
- Custom window functions

Examples:
    >>> from earnorm.base.database.query.core.operations import WindowOperation
    >>> from earnorm.types import DatabaseModel

    >>> class Employee(DatabaseModel):
    ...     name: str
    ...     department: str
    ...     salary: float
    ...     hire_date: datetime

    >>> # Create window operation
    >>> window = WindowOperation(Employee)

    >>> # Row number by department
    >>> results = await window.over(
    ...     partition_by=["department"]
    ... ).order_by(
    ...     "-salary"
    ... ).row_number(
    ...     "rank_in_dept"
    ... ).execute()

    >>> # Running total by department
    >>> results = await window.over(
    ...     partition_by=["department"]
    ... ).order_by(
    ...     "hire_date"
    ... ).sum(
    ...     "salary",
    ...     "running_total"
    ... ).execute()

    >>> # Moving average
    >>> results = await window.over(
    ...     order_by=["hire_date"]
    ... ).frame(
    ...     "rows",
    ...     start=-2,
    ...     end=0
    ... ).avg(
    ...     "salary",
    ...     "moving_avg"
    ... ).execute()
"""

from typing import Any, List, Optional, TypeVar

from earnorm.base.database.query.core.operations.base import BaseOperation
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class BaseWindow(BaseOperation[ModelT], WindowProtocol[ModelT]):
    """Base class for window operations.

    This class provides common functionality for window operations.
    Database-specific window implementations should inherit from this class.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize window operation."""
        super().__init__()
        self._partition_by: List[str] = []
        self._order_by: List[str] = []
        self._window_expr: Optional[JsonDict] = None
        self._alias: Optional[str] = None

    def over(
        self,
        partition_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
    ) -> "BaseWindow[ModelT]":
        """Set window clause.

        Args:
            partition_by: Fields to partition by
            order_by: Fields to order by

        Returns:
            Self for chaining
        """
        if partition_by:
            self._partition_by = partition_by
        if order_by:
            self._order_by = order_by
        return self

    def as_(self, alias: str) -> str:
        """Set alias for window expression.

        Args:
            alias: Alias name

        Returns:
            Window expression with alias
        """
        self._alias = alias
        return f"{self._window_expr} AS {alias}" if self._window_expr else alias

    def row_number(self, alias: str = "row_number") -> "BaseWindow[ModelT]":
        """ROW_NUMBER() window function.

        Returns:
            Window expression
        """
        self._window_expr = {"$rowNumber": {}}
        return self

    def rank(self, alias: str = "rank") -> "BaseWindow[ModelT]":
        """RANK() window function.

        Returns:
            Window expression
        """
        self._window_expr = {"$rank": {}}
        return self

    def dense_rank(self, alias: str = "dense_rank") -> "BaseWindow[ModelT]":
        """DENSE_RANK() window function.

        Returns:
            Window expression
        """
        self._window_expr = {"$denseRank": {}}
        return self

    def first_value(self, field: str) -> "BaseWindow[ModelT]":
        """FIRST_VALUE() window function.

        Args:
            field: Field to get first value of

        Returns:
            Window expression
        """
        self._window_expr = {
            "$first": {"$" + field},
            "window": {"documents": ["unbounded", "current"]},
        }
        return self

    def last_value(self, field: str) -> "BaseWindow[ModelT]":
        """LAST_VALUE() window function.

        Args:
            field: Field to get last value of

        Returns:
            Window expression
        """
        self._window_expr = {
            "$last": {"$" + field},
            "window": {"documents": ["current", "unbounded"]},
        }
        return self

    def lag(
        self, field: str, offset: int = 1, default: Any = None
    ) -> "BaseWindow[ModelT]":
        """LAG() window function.

        Args:
            field: Field to lag
            offset: Number of rows to lag
            default: Default value if no row exists

        Returns:
            Window expression
        """
        self._window_expr = {
            "$shift": {
                "output": "$" + field,
                "by": offset,
                "default": default,
            }
        }
        return self

    def lead(
        self, field: str, offset: int = 1, default: Any = None
    ) -> "BaseWindow[ModelT]":
        """LEAD() window function.

        Args:
            field: Field to lead
            offset: Number of rows to lead
            default: Default value if no row exists

        Returns:
            Window expression
        """
        self._window_expr = {
            "$shift": {
                "output": "$" + field,
                "by": -offset,
                "default": default,
            }
        }
        return self

    def validate(self) -> None:
        """Validate window configuration.

        Raises:
            ValueError: If window configuration is invalid
        """
        if not self._window_expr:
            raise ValueError("Window function not specified")

    @property
    def partition_by(self) -> List[str]:
        """Get partition by fields.

        Returns:
            List of fields to partition by
        """
        return self._partition_by

    @property
    def order_by(self) -> List[str]:
        """Get order by fields.

        Returns:
            List of fields to order by
        """
        return self._order_by

    @property
    def window_expr(self) -> Optional[JsonDict]:
        """Get window expression.

        Returns:
            Window expression
        """
        return self._window_expr

    @property
    def alias(self) -> Optional[str]:
        """Get alias.

        Returns:
            Alias name
        """
        return self._alias
