"""Set field type."""

from typing import Any, List, Optional, Set, Type, TypeVar

from earnorm.fields.base import Field
from earnorm.validators.types import ValidatorFunc

T = TypeVar("T")


class SetField(Field[Set[T]]):
    """Set field.

    Examples:
        >>> tags = SetField(StringField())
        >>> tags.convert(["python", "mongodb"])
        {"python", "mongodb"}
        >>> tags.convert({"python", "mongodb"})
        {"python", "mongodb"}
        >>> tags.convert(None)
        set()

        # With validation
        >>> numbers = SetField(IntegerField(), min_length=1, max_length=5)
        >>> numbers.convert([1, 2, 3])  # Valid
        {1, 2, 3}
        >>> numbers.convert([])  # Will raise ValidationError
        ValidationError: Set must have at least 1 item
    """

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            field: Field type for set items
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_length: Minimum set length
            max_length: Maximum set length
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.field = field
        if min_length is not None or max_length is not None:
            from earnorm.validators import validate_length

            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_length(min_length, max_length))  # type: ignore

    def _get_field_type(self) -> Type[Set[T]]:
        """Get field type.

        Returns:
            Type object representing set type
        """
        return set  # type: ignore

    def convert(self, value: Any) -> Set[T]:
        """Convert value to set.

        Args:
            value: Value to convert

        Returns:
            Converted set value or empty set if value is None

        Examples:
            >>> field = SetField(StringField())
            >>> field.convert(["a", "b"])
            {"a", "b"}
            >>> field.convert(None)
            set()
        """
        if value is None:
            return set()
        if isinstance(value, (list, tuple, set)):
            return {self.field.convert(item) for item in value}  # type: ignore
        return {self.field.convert(value)}  # type: ignore

    def to_mongo(self, value: Optional[Set[T]]) -> Optional[List[Any]]:
        """Convert Python set to MongoDB list.

        Args:
            value: Set value to convert

        Returns:
            MongoDB list value or None if value is None

        Examples:
            >>> field = SetField(StringField())
            >>> field.to_mongo({"a", "b"})
            ["a", "b"]
            >>> field.to_mongo(None)
            None
        """
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]  # type: ignore

    def from_mongo(self, value: Any) -> Set[T]:
        """Convert MongoDB list to Python set.

        Args:
            value: MongoDB value to convert

        Returns:
            Python set value or empty set if value is None

        Examples:
            >>> field = SetField(StringField())
            >>> field.from_mongo(["a", "b"])
            {"a", "b"}
            >>> field.from_mongo(None)
            set()
        """
        if value is None:
            return set()
        if isinstance(value, (list, tuple)):
            return {self.field.from_mongo(item) for item in value}  # type: ignore
        return {self.field.from_mongo(value)}  # type: ignore
