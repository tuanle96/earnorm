"""Tuple field type."""

from typing import Any, List, Optional, Tuple, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.validators.types import ValidatorFunc

T = TypeVar("T")


class TupleField(Field[Tuple[T, ...]]):
    """Tuple field.

    Examples:
        >>> coordinates = TupleField(FloatField(), length=2)
        >>> coordinates.convert([1.0, 2.0])
        (1.0, 2.0)
        >>> coordinates.convert((1.0, 2.0))
        (1.0, 2.0)
        >>> coordinates.convert(None)
        ()

        # With validation
        >>> point = TupleField(IntegerField(), length=3)
        >>> point.convert([1, 2, 3])  # Valid
        (1, 2, 3)
        >>> point.convert([1, 2])  # Will raise ValidationError
        ValidationError: Tuple must have exactly 3 items
    """

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            field: Field type for tuple items
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            length: Required tuple length
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.field = field
        self.length = length
        if length is not None:
            from earnorm.validators import validate_length

            self._metadata.validators.append(validate_length(length, length))

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return tuple

    def convert(self, value: Any) -> Tuple[T, ...]:
        """Convert value to tuple."""
        if value is None:
            return tuple()
        if isinstance(value, (list, tuple)):
            return tuple(self.field.convert(item) for item in value)  # type: ignore
        return (self.field.convert(value),)

    def to_mongo(self, value: Optional[Tuple[T, ...]]) -> Optional[List[Any]]:
        """Convert Python tuple to MongoDB list."""
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]  # type: ignore

    def from_mongo(self, value: Any) -> Tuple[T, ...]:
        """Convert MongoDB list to Python tuple."""
        if value is None:
            return tuple()
        if isinstance(value, (list, tuple)):
            return tuple(self.field.from_mongo(item) for item in value)  # type: ignore
        return (self.field.from_mongo(value),)
