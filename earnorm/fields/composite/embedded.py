"""Embedded document field type."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.types import ModelInterface
from earnorm.validators.types import ValidatorFunc

M = TypeVar("M", bound=ModelInterface)


class EmbeddedField(Field[M]):
    """Embedded document field.

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
        """Get field type."""
        return self.model_class

    def convert(self, value: Any) -> M:
        """Convert value to model instance."""
        if value is None:
            return self.model_class()
        if isinstance(value, dict):
            return self.model_class(**value)
        if isinstance(value, self.model_class):
            return value
        raise ValueError(f"Cannot convert {type(value)} to {self.model_class.__name__}")

    def to_mongo(self, value: Optional[M]) -> Optional[Dict[str, Any]]:
        """Convert Python model to MongoDB document."""
        if value is None:
            return None
        return value.to_mongo()

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB document to Python model."""
        if value is None:
            return self.model_class()
        if isinstance(value, dict):
            return self.model_class.from_mongo(Dict[str, Any](value))  # type: ignore
        raise ValueError(f"Cannot convert {type(value)} to {self.model_class.__name__}")
