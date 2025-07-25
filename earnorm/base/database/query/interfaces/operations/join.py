"""Join operation interface.

This module defines the interface for join operations.
All database-specific join implementations must implement this interface.

Examples:
    >>> # Using join interface
    >>> query.join(Post).on(User.id == Post.user_id)
    >>> query.left_join(Comment).on(Post.id == Comment.post_id)
"""

from abc import abstractmethod
from typing import Any, Generic, TypeVar

from earnorm.base.database.query.interfaces.operations.base import OperationProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class JoinProtocol(OperationProtocol[ModelT], Generic[ModelT, JoinT]):
    """Protocol for join operations."""

    @abstractmethod
    def join(
        self,
        model: str | type[JoinT],
        on: dict[str, Any] | None = None,
        join_type: str = "inner",
    ) -> "JoinProtocol[ModelT, JoinT]":
        """Add join condition.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Join clause builder
        """
        ...

    @abstractmethod
    def on(self, *conditions: Any) -> "JoinProtocol[ModelT, JoinT]":
        """Add join conditions.

        Args:
            conditions: Join conditions

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def inner(self) -> "JoinProtocol[ModelT, JoinT]":
        """Make this an inner join.

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def left(self) -> "JoinProtocol[ModelT, JoinT]":
        """Make this a left join.

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def right(self) -> "JoinProtocol[ModelT, JoinT]":
        """Make this a right join.

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def full(self) -> "JoinProtocol[ModelT, JoinT]":
        """Make this a full join.

        Returns:
            Self for chaining
        """
        ...

    @abstractmethod
    def cross(self) -> "JoinProtocol[ModelT, JoinT]":
        """Make this a cross join.

        Returns:
            Self for chaining
        """
        ...

    def validate(self) -> None:
        """Validate join configuration.

        Raises:
            ValueError: If join configuration is invalid
        """
        ...

    def get_pipeline_stages(self) -> list[JsonDict]:
        """Get MongoDB aggregation pipeline stages for this join.

        Returns:
            List[JsonDict]: List of pipeline stages
        """
        ...
