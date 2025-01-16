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

            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_length(length, length))  # type: ignore

    def _get_field_type(self) -> Type[Tuple[T, ...]]:
        """Get field type.

        Returns:
            Type object representing tuple type
        """
        return tuple  # type: ignore

    def convert(self, value: Any) -> Tuple[T, ...]:
        """Convert value to tuple.

        Args:
            value: Value to convert

        Returns:
            Converted tuple value or empty tuple if value is None

        Examples:
            >>> field = TupleField(IntegerField())
            >>> field.convert([1, 2, 3])
            (1, 2, 3)
            >>> field.convert(None)
            ()
        """
        if value is None:
            return tuple()
        if isinstance(value, (list, tuple)):
            return tuple(self.field.convert(item) for item in value)  # type: ignore
        return (self.field.convert(value),)  # type: ignore

    def to_mongo(self, value: Optional[Tuple[T, ...]]) -> Optional[List[Any]]:
        """Convert Python tuple to MongoDB list.

        Args:
            value: Tuple value to convert

        Returns:
            MongoDB list value or None if value is None

        Examples:
            >>> field = TupleField(IntegerField())
            >>> field.to_mongo((1, 2, 3))
            [1, 2, 3]
            >>> field.to_mongo(None)
            None
        """
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]  # type: ignore

    def from_mongo(self, value: Any) -> Tuple[T, ...]:
        """Convert MongoDB list to Python tuple.

        Args:
            value: MongoDB value to convert

        Returns:
            Python tuple value or empty tuple if value is None

        Examples:
            >>> field = TupleField(IntegerField())
            >>> field.from_mongo([1, 2, 3])
            (1, 2, 3)
            >>> field.from_mongo(None)
            ()
        """
        if value is None:
            return tuple()
        if isinstance(value, (list, tuple)):
            return tuple(self.field.from_mongo(item) for item in value)  # type: ignore
        return (self.field.from_mongo(value),)  # type: ignore
