"""List field type."""

from typing import Any, Generic, List, Optional, Type, TypeVar

from earnorm.fields.base import Field

T = TypeVar("T")


class ListField(Field[List[T]], Generic[T]):
    """List field for storing sequences of values.

    This field type stores lists of values, where each value is converted and validated
    using the provided field type.

    Type Parameters:
        T: The type of items in the list

    Attributes:
        field: Field instance used to convert and validate list items

    Examples:
        >>> # List of integers
        >>> numbers = ListField(IntField())
        >>> numbers.convert([1, "2", 3])  # Converts strings to ints
        [1, 2, 3]
        >>>
        >>> # List of embedded documents
        >>> class Address(BaseModel):
        ...     street = StringField()
        ...     city = StringField()
        >>> addresses = ListField(EmbeddedField(Address))
        >>> addresses.convert([
        ...     {"street": "123 Main St", "city": "New York"},
        ...     {"street": "456 Oak Ave", "city": "LA"}
        ... ])
    """

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        default: Optional[List[T]] = None,
    ) -> None:
        """Initialize list field.

        Args:
            field: Field instance used to convert and validate list items
            required: Whether the field is required
            default: Default value for the field

        Examples:
            >>> numbers = ListField(IntField(), required=True, default=[1, 2, 3])
        """
        super().__init__(
            required=required,
            default=default or [],
        )
        self.field = field

    def _get_field_type(self) -> Type[Any]:
        """Get field type.

        Returns:
            The list type

        Examples:
            >>> field = ListField(IntField())
            >>> field._get_field_type()
            <class 'list'>
        """
        return list

    def convert(self, value: Any) -> List[T]:
        """Convert value to list.

        Args:
            value: Value to convert

        Returns:
            List of converted values

        Raises:
            ValueError: If value is not a list
            ValidationError: If any item fails validation

        Examples:
            >>> field = ListField(IntField())
            >>> field.convert([1, "2", 3])
            [1, 2, 3]
            >>> field.convert(None)
            []
            >>> field.convert("not a list")  # Raises ValueError
        """
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.convert(item)
            result.append(converted)
        return result

    def to_dict(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert list to dict representation.

        Args:
            value: List to convert

        Returns:
            List of converted values, or None if input is None

        Examples:
            >>> class Address(BaseModel):
            ...     street = StringField()
            >>> field = ListField(EmbeddedField(Address))
            >>> addresses = [Address(street="123 Main St")]
            >>> field.to_dict(addresses)
            [{'street': '123 Main St'}]
        """
        if value is None:
            return None
        return [self.field.to_dict(item) for item in value]

    def to_mongo(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert Python list to MongoDB array.

        Args:
            value: List to convert

        Returns:
            List of converted values, or None if input is None

        Examples:
            >>> field = ListField(ObjectIdField())
            >>> field.to_mongo(["507f1f77bcf86cd799439011"])
            [ObjectId('507f1f77bcf86cd799439011')]
        """
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]

    def from_mongo(self, value: Any) -> List[T]:
        """Convert MongoDB array to Python list.

        Args:
            value: MongoDB array to convert

        Returns:
            List of converted values

        Raises:
            ValueError: If value is not a list

        Examples:
            >>> field = ListField(ObjectIdField())
            >>> field.from_mongo([ObjectId('507f1f77bcf86cd799439011')])
            ['507f1f77bcf86cd799439011']
        """
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.from_mongo(item)
            result.append(converted)
        return result
