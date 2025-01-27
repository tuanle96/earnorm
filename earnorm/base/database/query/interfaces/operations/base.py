"""Base operation interface.

This module defines the base interface for all query operations.
All operation-specific interfaces must inherit from this interface.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class OperationProtocol(Generic[ModelT], ABC):
    """Base protocol for all query operations."""

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
