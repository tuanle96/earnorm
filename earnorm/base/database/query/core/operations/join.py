"""Join operation implementation.

This module provides base implementation for join operations.
All database-specific join implementations should inherit from this class.

Examples:
    >>> class MongoJoin(BaseJoin[User, Post]):
    ...     def to_pipeline(self) -> list[JsonDict]:
    ...         return [
    ...             {
    ...                 "$lookup": {
    ...                     "from": "posts",
    ...                     "localField": "id",
    ...                     "foreignField": "user_id",
    ...                     "as": "posts"
    ...                 }
    ...             }
    ...         ]
"""

from typing import Dict, Literal, Optional, Protocol, Type, TypeVar, Union

from earnorm.base.database.query.core.operations.base import BaseOperation
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)

JoinType = Literal["inner", "left", "right", "cross", "full"]


class Comparable(Protocol):
    """Protocol for objects that support comparison."""

    last_comparison: tuple[str, str, str]


class BaseJoin(BaseOperation[ModelT], JoinProtocol[ModelT, JoinT]):
    """Base class for join operations.

    This class provides common functionality for join operations.
    Database-specific join implementations should inherit from this class.

    Args:
        ModelT: Type of model being queried
        JoinT: Type of model being joined
    """

    def __init__(self) -> None:
        """Initialize join operation."""
        super().__init__()
        self._model: Optional[Union[str, Type[JoinT]]] = None
        self._conditions: Dict[str, str] = {}
        self._join_type: str = "inner"  # Use str to match protocol

    def join(
        self,
        model: Union[str, Type[JoinT]],
        on: Optional[Dict[str, str]] = None,
        join_type: str = "inner",  # Use str to match protocol
    ) -> "BaseJoin[ModelT, JoinT]":
        """Add join condition.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Self for chaining
        """
        self._model = model
        if on:
            self._conditions.update(on)
        self._join_type = join_type
        return self

    def on(
        self, *conditions: Union[tuple[str, str, str], str, Comparable]
    ) -> "BaseJoin[ModelT, JoinT]":
        """Add join conditions.

        Args:
            conditions: Join conditions

        Returns:
            Self for chaining
        """
        for condition in conditions:
            if isinstance(condition, tuple):
                left, _, right = condition
                self._conditions[str(left)] = str(right)
            elif isinstance(condition, str):
                # Handle field == field case
                left, right = condition.split(" == ")
                self._conditions[left] = right
            else:
                # Handle field comparison case
                left, _, right = condition.last_comparison
                self._conditions[str(left)] = str(right)
        return self

    def inner(self) -> "BaseJoin[ModelT, JoinT]":
        """Make this an inner join.

        Returns:
            Self for chaining
        """
        self._join_type = "inner"
        return self

    def left(self) -> "BaseJoin[ModelT, JoinT]":
        """Make this a left join.

        Returns:
            Self for chaining
        """
        self._join_type = "left"
        return self

    def right(self) -> "BaseJoin[ModelT, JoinT]":
        """Make this a right join.

        Returns:
            Self for chaining
        """
        self._join_type = "right"
        return self

    def full(self) -> "BaseJoin[ModelT, JoinT]":
        """Make this a full join.

        Returns:
            Self for chaining
        """
        self._join_type = "full"
        return self

    def cross(self) -> "BaseJoin[ModelT, JoinT]":
        """Make this a cross join.

        Returns:
            Self for chaining
        """
        self._join_type = "cross"
        return self

    def validate(self) -> None:
        """Validate join configuration.

        Raises:
            ValueError: If join configuration is invalid
        """
        if not self._model:
            raise ValueError("Join model not specified")
        if not self._conditions and self._join_type != "cross":
            raise ValueError("Join conditions not specified")
        if self._join_type not in ("inner", "left", "right", "cross", "full"):
            raise ValueError(f"Invalid join type: {self._join_type}")

    @property
    def model(self) -> Optional[Union[str, Type[JoinT]]]:
        """Get join model.

        Returns:
            Model to join with
        """
        return self._model

    @property
    def conditions(self) -> Dict[str, str]:
        """Get join conditions.

        Returns:
            Join conditions
        """
        return self._conditions

    @property
    def join_type(self) -> str:  # Use str to match protocol
        """Get join type.

        Returns:
            Join type
        """
        return self._join_type
