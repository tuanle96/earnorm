"""Base field implementation.

This module provides the base field class that all field types inherit from.
It handles:
- Field setup and initialization
- Value validation and conversion
- Type checking and constraints
"""

from typing import Any, Dict, Generic, Optional, Tuple, TypeVar, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.adapters.base import DatabaseAdapter
from earnorm.fields.types import DatabaseValue

T = TypeVar("T")  # Field value type

# Type aliases for validation
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidatorCallable = Any  # TODO: Fix this when mypy supports async callable with TypeVar


class BaseField(Generic[T]):
    """Base class for all field types.

    This class provides common functionality for all fields:
    - Field setup and initialization
    - Value validation and conversion
    - Type checking and constraints

    Args:
        **kwargs: Field options passed to subclasses.
    """

    name: str
    model_name: str
    _value: Optional[T]
    _options: Dict[str, Any]
    required: bool
    readonly: bool
    store: bool
    index: bool
    help: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize field.

        Args:
            **kwargs: Field options passed to subclasses.
        """
        self.name: str = ""
        self.model_name: str = ""
        self._value: Optional[T] = None
        self._options = kwargs
        self.required = kwargs.get("required", True)
        self.readonly = kwargs.get("readonly", False)
        self.store = kwargs.get("store", True)
        self.index = kwargs.get("index", False)
        self.help = kwargs.get("help", "")
        self.compute = kwargs.get("compute")
        self.depends = kwargs.get("depends", [])
        self.validators = kwargs.get("validators", [])
        self.adapters: Dict[str, DatabaseAdapter[T]] = {}

    @property
    def default(self) -> Optional[Any]:
        """Get field default value.

        Returns:
            Optional[Any]: Default value or None if not set
        """
        return self._options.get("default")

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name.
            model_name: Model name.
        """
        self.name = name
        self.model_name = model_name

    def register_adapter(self, adapter: DatabaseAdapter[T]) -> None:
        """Register database adapter.

        Args:
            adapter: Database adapter instance
        """
        self.adapters[adapter.backend_name] = adapter

    async def validate(self, value: Optional[T]) -> Optional[T]:
        """Validate field value.

        Args:
            value: Value to validate.

        Returns:
            The validated value.

        Raises:
            FieldValidationError: If validation fails.
        """
        if value is None and self.required:
            raise FieldValidationError(
                message="Field is required",
                field_name=self.name,
            )

        # Run validators
        for validator in self.validators:
            result: ValidatorResult = await validator(value)
            if isinstance(result, tuple):
                valid, message = result
            else:
                valid, message = bool(result), "Validation failed"

            if not valid:
                raise FieldValidationError(
                    message=str(message),
                    field_name=self.name,
                )

        return value

    def __get__(self, instance: Any, owner: Any) -> Union["BaseField[T]", Optional[T]]:
        """Get field value.

        Args:
            instance: Model instance.
            owner: Model class.

        Returns:
            Union[BaseField[T], Optional[T]]: Field instance if accessed on class,
                or field value if accessed on instance.
        """
        if instance is None:
            return self
        return self._value

    def __set__(self, instance: Any, value: Optional[T]) -> None:
        """Set field value.

        Args:
            instance: Model instance.
            value: Value to set.
        """
        self._value = value

    async def convert(self, value: Any) -> Optional[T]:
        """Convert value to field type.

        This method should be overridden by subclasses to implement
        type-specific conversion logic.

        Args:
            value: Value to convert

        Returns:
            Optional[T]: Converted value
        """
        return cast(Optional[T], value)

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Database value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].to_db_value(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to Python format.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Optional[T]: Python value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].from_db_value(value)

    def get_backend_options(self, backend: str) -> Dict[str, Any]:
        """Get database-specific options.

        Args:
            backend: Database backend type

        Returns:
            Dict[str, Any]: Backend options

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return {
            "type": self.adapters[backend].get_field_type(),
            **self.adapters[backend].get_field_options(),
        }

    def setup_triggers(self) -> None:
        """Setup compute triggers.

        This method is called after field setup to initialize any compute triggers.
        It should be overridden by subclasses that need trigger functionality.
        """
        if self.compute:
            # TODO: Implement compute triggers
            pass

    def copy(self) -> "BaseField[T]":
        """Create copy of field.

        Returns:
            BaseField[T]: New field instance with same configuration
        """
        return self.__class__(**self._options)
