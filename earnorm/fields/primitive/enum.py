"""Enum field type."""

from enum import Enum
from typing import Any, List, Optional, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.validators.types import ValidatorFunc

E = TypeVar("E", bound=Enum)


class EnumField(Field[E]):
    """Enum field.

    Examples:
        >>> from enum import Enum
        >>> class Status(Enum):
        ...     ACTIVE = "active"
        ...     INACTIVE = "inactive"
        ...
        >>> status = EnumField(Status)
        >>> status.convert("active")
        <Status.ACTIVE: 'active'>
        >>> status.convert(Status.INACTIVE)
        <Status.INACTIVE: 'inactive'>
        >>> status.convert(None)
        <Status.INACTIVE: 'inactive'>  # Default value
    """

    def __init__(
        self,
        enum_class: Type[E],
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            enum_class: Enum class
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
        self.enum_class = enum_class
        # Get first enum value as default
        self._default_value = next(iter(self.enum_class))

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return self.enum_class

    def convert(self, value: Any) -> E:
        """Convert value to enum."""
        if value is None:
            return self._default_value
        if isinstance(value, self.enum_class):
            return value
        try:
            return self.enum_class(value)
        except ValueError:
            try:
                return self.enum_class[str(value).upper()]
            except KeyError as e:
                raise ValueError(
                    f"Invalid value for enum {self.enum_class.__name__}: {value}"
                ) from e

    def to_mongo(self, value: Optional[E]) -> Optional[str]:
        """Convert Python enum to MongoDB string."""
        if value is None:
            return None
        return value.value

    def from_mongo(self, value: Any) -> E:
        """Convert MongoDB string to Python enum."""
        if value is None:
            return self._default_value
        return self.enum_class(value)
