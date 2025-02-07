"""Field descriptors for model fields.

This module provides descriptors for model fields to handle:
- Async field access
- Field validation
- Field conversion
- Field caching
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

from earnorm.fields.base import BaseField

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncFieldDescriptor:
    """Descriptor for async field access.

    This descriptor handles:
    - Async field access
    - Field caching
    - Field validation

    Examples:
        >>> class User(BaseModel):
        ...     name = AsyncFieldDescriptor(StringField())
        >>> user = User()
        >>> await user.name  # Fetches from DB and caches
        >>> await user.name  # Returns from cache
    """

    def __init__(self, field: BaseField[Any]) -> None:
        """Initialize descriptor.

        Args:
            field: Field instance
        """
        self.field = field
        self.name = field.name if hasattr(field, "name") else None

    async def __get__(
        self, instance: Optional["BaseModel"], owner: Type["BaseModel"]
    ) -> Any:
        """Get field value.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Field value
        """
        if instance is None:
            return self.field

        try:
            if not self.name:
                raise AttributeError("Field name not set")

            # Get value using __getattr__
            value = await instance.__getattr__(self.name)
            return value
        except Exception as e:
            logger.error(f"Failed to get field {self.name}: {str(e)}")
            raise

    async def __set__(self, instance: "BaseModel", value: Any) -> None:
        """Set field value.

        Args:
            instance: Model instance
            value: Value to set
        """
        if not instance:
            return

        try:
            if not self.name:
                raise AttributeError("Field name not set")

            # Validate value
            await self.field.validate(value)

            # Update cache
            cache = object.__getattribute__(instance, "_cache")
            if isinstance(cache, dict):
                cache[self.name] = value

        except Exception as e:
            logger.error(f"Failed to set field {self.name}: {str(e)}")
            raise


class FieldsDescriptor:
    """Descriptor for model fields.

    This descriptor handles:
    - Field registration
    - Field inheritance
    - Field access
    """

    def __get__(
        self, instance: Optional["BaseModel"], owner: Type["BaseModel"]
    ) -> Dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Fields dictionary
        """
        return owner.__dict__.get("__fields__", {})
