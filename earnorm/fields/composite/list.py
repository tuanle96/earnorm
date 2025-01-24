"""List field implementation.

This module provides list field types for handling lists of values.
It supports:
- Lists of any field type
- Minimum and maximum length validation
- Unique value constraints
- Default values
- Nested validation

Examples:
    >>> class Post(Model):
    ...     tags = ListField(StringField(), default=list)
    ...     categories = ListField(StringField(), min_length=1)
    ...     ratings = ListField(IntegerField(), unique=True)
    ...     comments = ListField(EmbeddedField(CommentModel))
"""

from typing import Any, Generic, List, Optional, Set, Type, TypeVar, Union, cast

from earnorm.fields.base import Field, ValidationError

T = TypeVar("T")  # Type of list items


class ListField(Field[List[T]], Generic[T]):
    """Field for list values.

    Attributes:
        value_field: Field type for list values
        min_length: Minimum list length
        max_length: Maximum list length
        unique: Whether values must be unique
    """

    def __init__(
        self,
        value_field: Field[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        unique: bool = False,
        default: Optional[Union[List[T], Type[List[Any]]]] = None,
        **options: Any,
    ) -> None:
        """Initialize list field.

        Args:
            value_field: Field type for list values
            min_length: Minimum list length
            max_length: Maximum list length
            unique: Whether values must be unique
            default: Default value or list type
            **options: Additional field options
        """
        # Handle default value
        processed_default: Optional[List[T]] = None
        if default is not None:
            if default is list:
                processed_default = cast(List[T], [])
            else:
                processed_default = cast(List[T], default)

        super().__init__(default=processed_default, **options)
        self.value_field = value_field
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "array",
                },
                "postgres": {
                    "type": "JSONB",
                },
                "mysql": {
                    "type": "JSON",
                },
            }
        )

        # Set up value field
        self.value_field.name = f"{self.name}[*]"
        self.value_field.required = True  # List items can't be None

    async def validate(self, value: Any) -> None:
        """Validate list value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, list):
                raise ValidationError("Value must be a list", self.name)

            value_list = cast(List[Any], value)
            if self.min_length is not None and len(value_list) < self.min_length:
                raise ValidationError(
                    f"List must have at least {self.min_length} items",
                    self.name,
                )

            if self.max_length is not None and len(value_list) > self.max_length:
                raise ValidationError(
                    f"List must have at most {self.max_length} items",
                    self.name,
                )

            # Validate each item
            seen: Set[Any] = set()
            for i, item in enumerate(value_list):
                try:
                    await self.value_field.validate(item)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid item at index {i}: {str(e)}",
                        self.name,
                    )

                if self.unique:
                    if item in seen:
                        raise ValidationError(
                            f"Duplicate value at index {i}",
                            self.name,
                        )
                    seen.add(item)

    async def convert(self, value: Any) -> Optional[List[T]]:
        """Convert value to list.

        Args:
            value: Value to convert

        Returns:
            List value

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, str):
                # Try to parse as JSON array
                import json

                try:
                    value = json.loads(value)
                    if not isinstance(value, list):
                        raise ValidationError(
                            "JSON value must be an array",
                            self.name,
                        )
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        f"Invalid JSON array: {str(e)}",
                        self.name,
                    )
            elif not isinstance(value, list):
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to list",
                    self.name,
                )

            # Convert each item
            value_list = cast(List[Any], value)
            result: List[T] = []
            for i, item in enumerate(value_list):
                try:
                    converted = await self.value_field.convert(item)
                    if converted is None:
                        raise ValidationError(
                            "List items cannot be None",
                            self.name,
                        )
                    result.append(converted)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid item at index {i}: {str(e)}",
                        self.name,
                    )

            return result
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def to_db(
        self, value: Optional[List[T]], backend: str
    ) -> Optional[List[Any]]:
        """Convert list to database format.

        Args:
            value: List value
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        result: List[Any] = []
        for item in value:
            db_value = await self.value_field.to_db(item, backend)
            result.append(db_value)

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[List[T]]:
        """Convert database value to list.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            List value
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValidationError(
                f"Expected list from database, got {type(value).__name__}",
                self.name,
            )

        value_list = cast(List[Any], value)
        result: List[T] = []
        for item in value_list:
            converted = await self.value_field.from_db(item, backend)
            if converted is None:
                raise ValidationError(
                    "List items cannot be None",
                    self.name,
                )
            result.append(converted)

        return result
