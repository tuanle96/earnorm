"""Base field types for EarnORM.

This module provides the base field class that all field types inherit from.
It implements the core functionality for field validation, conversion, and serialization.
"""

from abc import abstractmethod
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar, Union

from typing_extensions import Self

from earnorm.base.fields.metadata import FieldMetadata
from earnorm.di import container
from earnorm.types import FieldProtocol, ModelInterface
from earnorm.validators import ValidationError

T = TypeVar("T")
M = TypeVar("M", bound=ModelInterface)
ValidatorFunc = Callable[[Any], None]


class Field(FieldProtocol, Generic[T]):
    """Base field class.

    This class implements the FieldProtocol and provides the core functionality
    for all field types. It handles field validation, conversion between Python
    and MongoDB types, and serialization.

    Type Parameters:
        T: The Python type this field represents

    Attributes:
        name: Name of the field
        _metadata: Field metadata containing configuration
        _cache_manager: Cache manager for caching field operations
    """

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        index: bool = False,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether the field is required
            unique: Whether the field value must be unique
            default: Default value for the field
            validators: List of validator functions
            index: Whether to create an index for this field
            description: Field description
            **kwargs: Additional field options
        """
        self.name: str = ""
        self._metadata = FieldMetadata(
            name=self.name,
            field_type=self._get_field_type(),
            required=required,
            unique=unique,
            default=default,
            validators=validators or [],
            index=index,
            description=description,
            options=kwargs,
        )
        self._cache_manager = container.get("cache_lifecycle_manager")

    def _get_field_type(self) -> Type[Any]:
        """Get field type.

        Returns:
            Type object representing this field's type
        """
        return type(Any)

    @property
    def metadata(self) -> FieldMetadata:
        """Get field metadata.

        Returns:
            FieldMetadata object containing field configuration
        """
        return self._metadata

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        try:
            self._metadata.validate(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    def __get__(
        self, instance: Optional[ModelInterface], owner: Type[ModelInterface]
    ) -> Union[Self, T]:
        """Get field value.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Field value if instance is provided, otherwise returns self
        """
        if instance is None:
            return self
        value = instance.data.get(self.name)  # type: ignore
        if value is None:
            return self.convert(self._metadata.default)
        return self.from_mongo(value)

    def __set__(self, instance: Optional[ModelInterface], value: Any) -> None:
        """Set field value.

        Args:
            instance: Model instance
            value: Value to set
        """
        if instance is None:
            return

        # Validate before setting
        self.validate(value)

        if isinstance(value, Field):
            instance.data[self.name] = self.convert(value._metadata.default)  # type: ignore
        else:
            instance.data[self.name] = self.convert(value)  # type: ignore

    def __delete__(self, instance: Optional[ModelInterface]) -> None:
        """Delete field value.

        Args:
            instance: Model instance
        """
        if instance is None:
            return
        instance.data.pop(self.name, None)  # type: ignore

    @abstractmethod
    def convert(self, value: Any) -> T:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value of type T
        """
        pass

    def to_dict(self, value: Optional[T]) -> Any:
        """Convert value to dict representation.

        Args:
            value: Value to convert

        Returns:
            Dict representation of value
        """
        return value

    def to_mongo(self, value: Optional[T]) -> Any:
        """Convert Python value to MongoDB value.

        Args:
            value: Value to convert

        Returns:
            MongoDB representation of value
        """
        return value

    def from_mongo(self, value: Any) -> T:
        """Convert MongoDB value to Python value.

        Args:
            value: Value to convert

        Returns:
            Python value of type T
        """
        return self.convert(value)
