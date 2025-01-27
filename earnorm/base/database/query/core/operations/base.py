"""Base operation implementation.

This module provides base implementation for all query operations.
All operation-specific implementations should inherit from this class.

Examples:
    >>> class CustomOperation(BaseOperation[User]):
    ...     def to_pipeline(self) -> list[JsonDict]:
    ...         return [{"$match": {"age": {"$gt": 18}}}]
    ...
    ...     def validate(self) -> None:
    ...         if not self._is_valid:
    ...             raise ValueError("Invalid operation")
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

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
        self._pipeline: List[JsonDict] = []
        self._options: Dict[str, Any] = {}
        self._is_valid: bool = True
        self._error_message: Optional[str] = None

    @property
    def pipeline(self) -> List[JsonDict]:
        """Get current pipeline.

        Returns:
            List of pipeline stages
        """
        return self._pipeline

    @property
    def options(self) -> Dict[str, Any]:
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
    def error_message(self) -> Optional[str]:
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
    def to_pipeline(self) -> List[JsonDict]:
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
