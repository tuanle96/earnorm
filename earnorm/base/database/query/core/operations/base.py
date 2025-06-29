"""Base operation implementation.

This module provides the base operation class that all other operation types inherit from.
It implements common functionality for building and executing database operations.

The operation system supports:
- Operation chaining
- Result processing
- Type safety
- Custom operation handlers

Examples:
    >>> from earnorm.base.database.query.core.operations import Operation
    >>> from earnorm.types import DatabaseModel

    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int

    >>> # Create operation
    >>> op = Operation(User)
    >>> op.add_processor(lambda x: x.upper())
    >>> result = await op.execute()
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, Self, TypeVar

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class BaseOperation(Generic[ModelT], ABC):
    """Base class for all query operations.

    This class provides common functionality for all operations.
    Specific operations should inherit from this class and implement
    the required methods.

    Args:
        ModelT: Type of model being queried
    """

    def __init__(self) -> None:
        """Initialize operation."""
        self._pipeline: list[JsonDict] = []
        self._options: dict[str, Any] = {}
        self._is_valid: bool = True
        self._error_message: str | None = None

    @property
    def pipeline(self) -> list[JsonDict]:
        """Get current pipeline.

        Returns:
            List of pipeline stages
        """
        return self._pipeline

    @property
    def options(self) -> dict[str, Any]:
        """Get current options.

        Returns:
            Dictionary of options
        """
        return self._options

    @property
    def is_valid(self) -> bool:
        """Check if operation is valid.

        Returns:
            True if operation is valid
        """
        return self._is_valid

    @property
    def error_message(self) -> str | None:
        """Get error message if operation is invalid.

        Returns:
            Error message or None if operation is valid
        """
        return self._error_message

    def add_stage(self, stage: JsonDict) -> None:
        """Add pipeline stage.

        Args:
            stage: Pipeline stage to add
        """
        self._pipeline.append(stage)

    def add_option(self, key: str, value: Any) -> None:
        """Add option.

        Args:
            key: Option key
            value: Option value
        """
        self._options[key] = value

    def set_error(self, message: str) -> None:
        """Set error state.

        Args:
            message: Error message
        """
        self._is_valid = False
        self._error_message = message

    def clear_error(self) -> None:
        """Clear error state."""
        self._is_valid = True
        self._error_message = None

    def clear(self) -> None:
        """Clear operation state."""
        self._pipeline.clear()
        self._options.clear()
        self.clear_error()

    @abstractmethod
    def to_pipeline(self) -> list[JsonDict]:
        """Convert operation to database pipeline.

        Returns:
            List of pipeline stages
        """
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate operation configuration.

        Raises:
            ValueError: If operation configuration is invalid
        """
        pass


class Operation(Generic[ModelT]):
    """Base class for database operations.

    This class provides common functionality for all database operations.
    It implements operation chaining and result processing.

    Args:
        model_type: The model class to operate on

    Attributes:
        _model_type: The model class being operated on
        _processors: List of result processor functions

    Examples:
        >>> # Create operation
        >>> op = Operation(User)

        >>> # Add result processor
        >>> op.add_processor(lambda x: x.upper())

        >>> # Execute operation
        >>> result = await op.execute()
    """

    def __init__(self, model_type: type[ModelT]) -> None:
        """Initialize operation.

        Args:
            model_type: The model class to operate on
        """
        self._model_type = model_type
        self._processors: list[Callable[[Any], Any]] = []

    def add_processor(self, processor: Callable[[Any], Any]) -> Self:
        """Add result processor function.

        Processors are called in order for each result.

        Args:
            processor: Function that takes and returns a result

        Returns:
            Self for method chaining

        Examples:
            >>> def process_user(user):
            ...     user["full_name"] = f"{user['first_name']} {user['last_name']}"
            ...     return user
            ...
            >>> op.add_processor(process_user)
        """
        self._processors.append(processor)
        return self

    async def execute(self) -> Any:
        """Execute operation and return results.

        Returns:
            Operation results after processing

        Examples:
            >>> # Execute operation
            >>> result = await op.execute()

            >>> # Execute with processors
            >>> result = await op.add_processor(process).execute()
        """
        results = await self.to_pipeline()  # type: ignore
        for processor in self._processors:
            results = [processor(result) for result in results]  # type: ignore
        return results  # type: ignore
