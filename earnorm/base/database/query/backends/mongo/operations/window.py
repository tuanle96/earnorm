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

from typing import List, TypeVar

from earnorm.base.database.query.core.operations.window import BaseWindow
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoWindow(BaseWindow[ModelT]):
    """MongoDB window operation implementation.

    This class provides MongoDB-specific implementation for window operations.
    It uses MongoDB's $setWindowFields stage for window functions.

    Args:
        ModelT: Type of model being queried
    """

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
