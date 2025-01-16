"""Base field types for EarnORM.

This module provides the base field class that all field types inherit from.
It implements the core functionality for field validation, conversion, and serialization.
"""

from abc import abstractmethod
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar, Union

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
        required: Whether the field is required
        unique: Whether the field value must be unique
        default: Default value for the field
        _metadata: Field metadata containing configuration
        _cache_manager: Cache manager for caching field operations
    """

    name: str = ""
    required: bool = False
    unique: bool = False
    default: Any = None

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

        Examples:
            >>> field = Field(required=True, unique=True)
            >>> field = Field(default=42, validators=[validate_positive])
            >>> field = Field(index=True, description="User's age")
        """
        self.name = ""
        self.required = required
        self.unique = unique
        self.default = default
        self._metadata = FieldMetadata(
            field=self,
            name=self.name,
            required=required,
            unique=unique,
            default=default,
        )
        self._cache_manager = container.get("cache_lifecycle_manager")

    def _get_field_type(self) -> Type[T]:
        """Get field type.

        Returns:
            Type object representing this field's type T

        Examples:
            >>> field = IntField()
            >>> field._get_field_type()
            <class 'int'>
        """
        return type(Any)  # type: ignore

    @property
    def metadata(self) -> FieldMetadata:
        """Get field metadata.

        Returns:
            FieldMetadata object containing field configuration

        Examples:
            >>> field = Field(required=True)
            >>> field.metadata.required
            True
        """
        return self._metadata

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails

        Examples:
            >>> field = Field(validators=[lambda x: x > 0])
            >>> field.validate(42)  # OK
            >>> field.validate(-1)  # Raises ValidationError
        """
        try:
            self._metadata.validate(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(str(e))

    def __get__(
        self, instance: Optional[ModelInterface], owner: Type[ModelInterface]
    ) -> Union["Field[T]", T]:
        """Get field value.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Field value if instance is provided, otherwise returns self

        Examples:
            >>> class User(Model):
            ...     age = IntField()
            >>> user = User(age=42)
            >>> user.age  # Returns 42
            >>> User.age  # Returns IntField instance
        """
        if instance is None:
            return self
        value = instance.data.get(self.name)
        if value is None:
            return self.convert(self._metadata.default)
        return self.from_mongo(value)

    def __set__(self, instance: Optional[ModelInterface], value: Any) -> None:
        """Set field value.

        Args:
            instance: Model instance
            value: Value to set

        Examples:
            >>> class User(Model):
            ...     age = IntField()
            >>> user = User()
            >>> user.age = 42  # Sets age to 42
        """
        if instance is None:
            return

        # Validate before setting
        self.validate(value)

        if isinstance(value, Field):
            instance.data[self.name] = self.convert(value._metadata.default)
        else:
            instance.data[self.name] = self.convert(value)

    def __delete__(self, instance: Optional[ModelInterface]) -> None:
        """Delete field value.

        Args:
            instance: Model instance

        Examples:
            >>> class User(Model):
            ...     age = IntField()
            >>> user = User(age=42)
            >>> del user.age  # Removes age field
        """
        if instance is None:
            return
        instance.data.pop(self.name, None)

    @abstractmethod
    def convert(self, value: Any) -> T:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value of type T

        Examples:
            >>> field = IntField()
            >>> field.convert("42")
            42
        """
        pass

    def to_dict(self, value: Optional[T]) -> Any:
        """Convert value to dict representation.

        Args:
            value: Value to convert

        Returns:
            Dict representation of value

        Examples:
            >>> field = DateTimeField()
            >>> field.to_dict(datetime(2024, 1, 1))
            '2024-01-01T00:00:00'
        """
        return value

    def to_mongo(self, value: Optional[T]) -> Any:
        """Convert Python value to MongoDB value.

        Args:
            value: Value to convert

        Returns:
            MongoDB representation of value

        Examples:
            >>> field = ObjectIdField()
            >>> field.to_mongo("507f1f77bcf86cd799439011")
            ObjectId('507f1f77bcf86cd799439011')
        """
        return value

    def from_mongo(self, value: Any) -> T:
        """Convert MongoDB value to Python value.

        Args:
            value: Value to convert

        Returns:
            Python value of type T

        Examples:
            >>> field = ObjectIdField()
            >>> field.from_mongo(ObjectId('507f1f77bcf86cd799439011'))
            '507f1f77bcf86cd799439011'
        """
        return self.convert(value)
