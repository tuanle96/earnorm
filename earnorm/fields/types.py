"""Type definitions for field types.

This module provides protocol definitions for field types.
"""

from typing import Any, Dict, List, Protocol, Tuple, TypeVar, Union

T = TypeVar("T")  # Value type


class RelationProtocol(Protocol[T]):
    """Protocol for relation field types."""

    model: type
    related_name: str
    on_delete: str
    lazy: bool

    async def get_related(self, instance: Any) -> T:
        """Get related instance."""
        ...

    async def set_related(self, instance: Any, value: T) -> None:
        """Set related instance."""
        ...

    async def delete_related(self, instance: Any) -> None:
        """Delete related instance."""
        ...


class ValidatorFunc(Protocol):
    """Protocol for validator functions."""

    async def __call__(self, value: Any) -> Union[bool, Tuple[bool, str]]:
        """Validate value.

        Args:
            value: Value to validate

        Returns:
            True if valid, or tuple of (False, error message) if invalid
        """
        ...


class FieldProtocol(Protocol[T]):
    """Protocol for field types."""

    name: str
    required: bool
    unique: bool
    validators: List[ValidatorFunc]
    backend_options: Dict[str, Any]

    async def validate(self, value: Any) -> None:
        """Validate value."""
        ...

    async def convert(self, value: Any) -> T:
        """Convert value."""
        ...

    async def to_db(self, value: T, backend: str) -> Any:
        """Convert to database format."""
        ...

    async def from_db(self, value: Any, backend: str) -> T:
        """Convert from database format."""
        ...
