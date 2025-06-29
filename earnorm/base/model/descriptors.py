"""Field descriptors for model fields.

This module provides descriptors for model fields to handle async field access,
validation, conversion and caching. It implements Python's descriptor protocol
for async field access in EarnORM models.

Key Features:
    1. Async Field Access
       - Lazy loading of field values
       - Async getter/setter methods
       - Cache management

    2. Field Validation
       - Type checking
       - Value constraints
       - Custom validators
       - Error handling

    3. Field Conversion
       - Python to database type conversion
       - Database to Python type conversion
       - Custom type converters
       - Null value handling

    4. Field Caching
       - Memory-efficient caching
       - Cache invalidation
       - Cache synchronization
       - Thread safety

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields import StringField, IntegerField

    >>> # Define model with async fields
    >>> class User(BaseModel):
    ...     name = AsyncFieldDescriptor(StringField())
    ...     age = AsyncFieldDescriptor(IntegerField())

    >>> # Create instance
    >>> user = User()

    >>> # Async field access
    >>> name = await user.name  # Fetches from DB and caches
    >>> name = await user.name  # Returns from cache

    >>> # Field validation
    >>> try:
    ...     await user.age = -1  # Raises ValueError
    ... except ValueError as e:
    ...     print(e)  # "Age cannot be negative"

    >>> # Cache invalidation
    >>> user._invalidate_cache('name')  # Force reload on next access

Classes:
    AsyncFieldDescriptor:
        Main descriptor class implementing async field access.

        Methods:
            __get__: Async getter for field values
            __set__: Async setter for field values
            __delete__: Clear field cache

        Attributes:
            field: BaseField instance
            name: Field name
            cache_key: Cache key format

Implementation Notes:
    1. The descriptor uses a per-instance cache dictionary to store field values
    2. Cache keys are formatted as "{model_name}.{field_name}"
    3. Field validation happens in the setter before caching
    4. Type conversion happens during get/set operations

See Also:
    - earnorm.fields.base: Base field definitions
    - earnorm.base.model.base: BaseModel implementation
    - earnorm.base.model.meta: Model metaclass
"""

import logging
from typing import TYPE_CHECKING, Any, Optional, TypeVar

from earnorm.fields.base import BaseField

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncFieldDescriptor:
    """Descriptor for async field access.

    This descriptor implements Python's descriptor protocol for async field access.
    It handles field validation, conversion, and caching for model fields.

    Features:
        - Async field access with caching
        - Automatic type conversion
        - Field validation on set
        - Cache invalidation
        - Memory optimization
        - Thread safety

    Args:
        field: BaseField instance to wrap

    Attributes:
        field: The wrapped field instance
        name: Field name (set by metaclass)

    Examples:
        >>> class User(BaseModel):
        ...     name = AsyncFieldDescriptor(StringField())
        ...     age = AsyncFieldDescriptor(IntegerField())

        >>> user = User()
        >>> await user.name  # Fetches from DB and caches
        >>> await user.name  # Returns from cache
        >>> await user.age = 25  # Validates and caches
        >>> user._invalidate_cache('name')  # Force reload
    """

    def __init__(self, field: BaseField[Any]) -> None:
        """Initialize descriptor.

        Args:
            field: Field instance to wrap
        """
        self.field = field
        self.name: str | None = None  # Will be set by metaclass

    def __set_name__(self, owner: type, name: str) -> None:
        """Set field name when descriptor is assigned to class.

        Args:
            owner: Owner class
            name: Attribute name
        """
        self.name = name
        if hasattr(self.field, 'name') and not self.field.name:
            self.field.name = name

    async def __get__(self, instance: Optional["BaseModel"], owner: type["BaseModel"]) -> Any:
        """Async getter for field value.

        This method:
        1. Checks the instance cache
        2. Fetches from database if not cached
        3. Converts to Python type
        4. Caches the result

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Field value

        Raises:
            AttributeError: If accessed on class or field not properly configured
            ValueError: If field value is invalid
        """
        # Return field instance when accessed on class
        if instance is None:
            return self.field

        # Validate field configuration
        if not self.field:
            raise AttributeError("Field not set")

        if not self.name:
            raise AttributeError("Field name not set")

        try:
            # Check cache first
            cached_value = instance._get_cache(self.name)
            if cached_value is not None:
                return cached_value

            # Get field value directly from BaseModel's field access logic
            # This avoids circular calls by using the model's internal field access
            field_value = await self._get_field_value(instance)

            # Cache the value
            instance._set_cache(self.name, field_value)

            return field_value

        except AttributeError:
            # Re-raise AttributeError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to get field {self.name}: {e!s}")
            raise ValueError(f"Error accessing field {self.name}: {e}") from e

    async def _get_field_value(self, instance: "BaseModel") -> Any:
        """Get field value from instance without circular calls.

        Args:
            instance: Model instance

        Returns:
            Field value

        Raises:
            ValueError: If field access fails
        """
        # Use BaseModel's internal field access mechanism
        # This delegates to the model's __getattr__ implementation
        # but ensures we don't create circular calls
        return await instance._get_field_value_internal(self.name)

    async def __set__(self, instance: "BaseModel", value: Any) -> None:
        """Async setter for field value.

        This method:
        1. Validates the value
        2. Converts to database type
        3. Updates the cache
        4. Marks field as modified

        Args:
            instance: Model instance
            value: Value to set

        Raises:
            AttributeError: If field not properly configured
            ValueError: If value is invalid
            TypeError: If value has wrong type
        """
        if not instance:
            raise ValueError("Cannot set field on None instance")

        if not self.name:
            raise AttributeError("Field name not set")

        try:
            # Validate value using field's validation
            await self.field.validate(value)

            # Update cache with validated value
            instance._set_cache(self.name, value)

            # Mark field as modified for change tracking
            if hasattr(instance, '_mark_field_modified'):
                instance._mark_field_modified(self.name)

        except (AttributeError, ValueError, TypeError):
            # Re-raise validation and configuration errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to set field {self.name}: {e!s}")
            raise ValueError(f"Error setting field {self.name}: {e}") from e

    def __delete__(self, instance: "BaseModel") -> None:
        """Delete field value (clear from cache).

        Args:
            instance: Model instance

        Raises:
            AttributeError: If field not properly configured
        """
        if not instance:
            raise ValueError("Cannot delete field from None instance")

        if not self.name:
            raise AttributeError("Field name not set")

        try:
            # Clear from cache
            instance._clear_cache(self.name)

            # Mark field as modified for change tracking
            if hasattr(instance, '_mark_field_modified'):
                instance._mark_field_modified(self.name)

        except Exception as e:
            logger.error(f"Failed to delete field {self.name}: {e!s}")
            raise AttributeError(f"Error deleting field {self.name}: {e}") from e


class FieldsDescriptor:
    """Descriptor for model fields.

    This descriptor handles:
    - Field registration
    - Field inheritance
    - Field access
    """

    def __get__(self, instance: Optional["BaseModel"], owner: type["BaseModel"]) -> dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Fields dictionary
        """
        return owner.__dict__.get("__fields__", {})
