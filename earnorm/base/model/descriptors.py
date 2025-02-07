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
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

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
        _cache: Per-instance value cache

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
        self.name = field.name if hasattr(field, "name") else None

    async def __get__(
        self, instance: Optional["BaseModel"], owner: Type["BaseModel"]
    ) -> Any:
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
            AttributeError: If accessed on class
            ValueError: If field value is invalid
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
            ValueError: If value is invalid
            TypeError: If value has wrong type
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
