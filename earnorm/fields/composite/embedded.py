"""Embedded document field type."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.types import ModelInterface
from earnorm.validators.types import ValidatorFunc

M = TypeVar("M", bound=ModelInterface)


class EmbeddedField(Field[M]):
    """Embedded document field.

    This field type allows embedding one document inside another. The embedded
    document is an instance of a model class that implements ModelInterface.

    Type Parameters:
        M: Type of the embedded model

    Attributes:
        model_class: Class of the embedded model

    Examples:
        >>> class Address(BaseModel):
        ...     street = StringField()
        ...     city = StringField()
        ...     country = StringField()
        ...
        >>> class User(BaseModel):
        ...     name = StringField()
        ...     address = EmbeddedField(Address)
        ...
        >>> user = User(name="John")
        >>> user.address = {"street": "123 Main St", "city": "New York", "country": "USA"}
        >>> print(user.address.street)
        '123 Main St'
        >>> print(user.address.city)
        'New York'
    """

    def __init__(
        self,
        model_class: Type[M],
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            model_class: Model class for embedded document
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            **kwargs: Additional field options

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> user = User(address=EmbeddedField(Address))
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.model_class = model_class

    def _get_field_type(self) -> Type[Any]:
        """Get field type.

        Returns:
            The embedded model class

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> field = EmbeddedField(Address)
            >>> field._get_field_type() == Address
            True
        """
        return self.model_class

    def convert(self, value: Any) -> M:
        """Convert value to model instance.

        Args:
            value: Value to convert

        Returns:
            Instance of the embedded model

        Raises:
            ValueError: If value cannot be converted to model instance

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> field = EmbeddedField(Address)
            >>> addr = field.convert({"street": "123 Main St"})
            >>> isinstance(addr, Address)
            True
        """
        if value is None:
            return self.model_class()
        if isinstance(value, dict):
            return self.model_class(**value)
        if isinstance(value, self.model_class):
            return value
        raise ValueError(f"Cannot convert {type(value)} to {self.model_class.__name__}")

    def to_mongo(self, value: Optional[M]) -> Optional[Dict[str, Any]]:
        """Convert Python model to MongoDB document.

        Args:
            value: Model instance to convert

        Returns:
            MongoDB document or None if input is None

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> field = EmbeddedField(Address)
            >>> addr = Address(street="123 Main St")
            >>> field.to_mongo(addr)
            {'street': '123 Main St'}
        """
        if value is None:
            return None
        return value.to_mongo()

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB document to Python model.

        Args:
            value: MongoDB document to convert

        Returns:
            Instance of the embedded model

        Raises:
            ValueError: If value cannot be converted to model instance

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> field = EmbeddedField(Address)
            >>> addr = field.from_mongo({"street": "123 Main St"})
            >>> isinstance(addr, Address)
            True
        """
        if value is None:
            return self.model_class()
        if isinstance(value, dict):
            model = self.model_class()
            model.from_mongo(value)  # type: ignore
            return model
        raise ValueError(f"Cannot convert {type(value)} to {self.model_class.__name__}")

    def validate(self, value: Any) -> None:
        """Validate embedded document.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
            ValueError: If value cannot be converted to model instance

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField(required=True)
            >>> field = EmbeddedField(Address, required=True)
            >>> field.validate({"street": "123 Main St"})  # OK
            >>> field.validate(None)  # Raises ValidationError
            >>> field.validate({"wrong": "value"})  # Raises ValidationError
        """
        super().validate(value)
        if value is not None:
            try:
                model = self.convert(value)
                if hasattr(model, "validate"):
                    model.validate()  # type: ignore
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid embedded document: {e}")
