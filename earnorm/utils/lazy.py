"""Lazy loading utilities.

This module provides utilities for lazy loading of related models.
"""

from typing import Any, Generic, Optional, Type, TypeVar, cast

from earnorm.types import ModelProtocol

T = TypeVar("T", bound=ModelProtocol)  # Model type


class LazyDescriptor(Generic[T]):
    """Descriptor for lazy loading of related models.

    Attributes:
        model: Model class
        id: Model instance ID
        instance: Loaded model instance
    """

    def __init__(self, model: Type[T], id: Any) -> None:
        """Initialize lazy descriptor.

        Args:
            model: Model class
            id: Model instance ID
        """
        self.model = model
        self.id = id
        self._instance: Optional[T] = None

    async def get(self) -> T:
        """Get model instance.

        Returns:
            Model instance
        """
        if self._instance is None:
            instance = await self.model.get(self.id)
            self._instance = cast(T, instance)
        return self._instance

    async def set(self, instance: T) -> None:
        """Set model instance.

        Args:
            instance: Model instance
        """
        self._instance = instance
        self.id = instance.id

    def __repr__(self) -> str:
        """Get string representation.

        Returns:
            String representation
        """
        return f"<LazyDescriptor {self.model.__name__}({self.id})>"
