"""MongoDB window operation implementation.

This module provides MongoDB-specific implementation for window operations.
It uses MongoDB's $setWindowFields stage for window functions.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> query = MongoQuery[User]()
    >>> query.window().over(partition_by=[User.age]).row_number()
"""

from typing import Any, Dict, List, Optional, TypeVar

from earnorm.base.database.query.core.operations.window import BaseWindow
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoWindow(BaseWindow[ModelT], WindowProtocol[ModelT]):
    """MongoDB window operation implementation.

    This class provides MongoDB-specific implementation for window operations.
    It uses MongoDB's $setWindowFields stage for window functions.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize MongoDB window."""
        super().__init__()
        self._partition_by: Optional[List[str]] = None
        self._order_by: Optional[List[str]] = None
        self._window_functions: List[Dict[str, Any]] = []

    def over(
        self,
        partition_by: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
    ) -> "MongoWindow[ModelT]":
        """Set window frame.

        Args:
            partition_by: Fields to partition by
            order_by: Fields to order by

        Returns:
            Self for chaining
        """
        self._partition_by = partition_by  # type: ignore
        self._order_by = order_by  # type: ignore
        return self

    def row_number(self, alias: str = "row_number") -> "MongoWindow[ModelT]":
        """Add row number.

        Args:
            alias: Alias for row number field

        Returns:
            Self for chaining
        """
        self._window_functions.append(
            {
                alias: {
                    "$function": {
                        "body": "function(partition_values, sort_values) { return partition_values.indexOf(sort_values) + 1; }",
                        "args": ["$partition_values", "$sort_values"],
                        "lang": "js",
                    }
                }
            }
        )
        return self

    def rank(self, alias: str = "rank") -> "MongoWindow[ModelT]":
        """Add rank.

        Args:
            alias: Alias for rank field

        Returns:
            Self for chaining
        """
        self._window_functions.append(
            {
                alias: {
                    "$function": {
                        "body": "function(partition_values, sort_values) { return partition_values.filter(v => v < sort_values).length + 1; }",
                        "args": ["$partition_values", "$sort_values"],
                        "lang": "js",
                    }
                }
            }
        )
        return self

    def dense_rank(self, alias: str = "dense_rank") -> "MongoWindow[ModelT]":
        """Add dense rank.

        Args:
            alias: Alias for dense rank field

        Returns:
            Self for chaining
        """
        self._window_functions.append(
            {
                alias: {
                    "$function": {
                        "body": "function(partition_values, sort_values) { return new Set(partition_values.filter(v => v <= sort_values)).size; }",
                        "args": ["$partition_values", "$sort_values"],
                        "lang": "js",
                    }
                }
            }
        )
        return self

    def validate(self) -> None:
        """Validate window configuration.

        Raises:
            ValueError: If window configuration is invalid
        """
        if not self._window_functions:
            raise ValueError("No window functions specified")

    def get_pipeline_stages(self) -> List[JsonDict]:
        """Get MongoDB aggregation pipeline stages for this window function.

        Returns:
            List[JsonDict]: List of pipeline stages
        """
        if not self._window_functions:
            return []

        stages: List[JsonDict] = []

        # Build $setWindowFields stage
        window_stage: JsonDict = {
            "$setWindowFields": {
                "partitionBy": (
                    {field: f"${field}" for field in self._partition_by}
                    if self._partition_by
                    else None
                ),
                "sortBy": (
                    {field: 1 for field in self._order_by} if self._order_by else None
                ),
                "output": {},
            }
        }

        # Add window functions
        for func in self._window_functions:
            window_stage["$setWindowFields"]["output"].update(func)

        stages.append(window_stage)

        return stages

    def to_pipeline(self) -> List[JsonDict]:
        """Convert window operation to MongoDB pipeline.

        Returns:
            List of pipeline stages

        Raises:
            ValueError: If window function is not supported by MongoDB
        """
        if not self._window_expr:
            raise ValueError("Window function not specified")

        # Build window stage
        window_stage = {
            "$setWindowFields": {
                "partitionBy": (
                    {field: f"${field}" for field in self._partition_by}
                    if self._partition_by
                    else None
                ),
                "sortBy": (
                    {field: 1 for field in self._order_by} if self._order_by else None
                ),
                "output": {
                    self._alias
                    or "window_result": {
                        **self._window_expr,
                        "window": (
                            {"documents": ["unbounded", "current"]}
                            if "window" not in self._window_expr
                            else self._window_expr["window"]
                        ),
                    }
                },
            }
        }

        # Remove None values
        if not window_stage["$setWindowFields"]["partitionBy"]:
            del window_stage["$setWindowFields"]["partitionBy"]
        if not window_stage["$setWindowFields"]["sortBy"]:
            del window_stage["$setWindowFields"]["sortBy"]

        return [window_stage]
