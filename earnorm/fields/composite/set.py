"""Set field implementation.

This module provides set field types for handling unique collections of values.
It supports:
- Sets of any field type
- Minimum and maximum size validation
- Default values
- Nested validation
- Automatic deduplication

Examples:
    >>> class User(Model):
    ...     roles = SetField(StringField(), default=set)
    ...     permissions = SetField(StringField(), min_size=1)
    ...     blocked_ips = SetField(IPAddressField())
    ...     favorite_tags = SetField(StringField(), max_size=10)
"""

from typing import (
    Any,
    Generic,
    Iterable,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
)

from earnorm.fields.base import Field, ValidationError

T = TypeVar("T")  # Type of set items


class SetField(Field[Set[T]], Generic[T]):
    """Field for set values.

    Attributes:
        value_field: Field type for set values
        min_size: Minimum set size
        max_size: Maximum set size
    """

    def __init__(
        self,
        value_field: Field[T],
        *,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        default: Optional[Union[Set[T], Type[Set[Any]]]] = None,
        **options: Any,
    ) -> None:
        """Initialize set field.

        Args:
            value_field: Field type for set values
            min_size: Minimum set size
            max_size: Maximum set size
            default: Default value or set type
            **options: Additional field options
        """
        # Handle default value
        processed_default: Optional[Set[T]] = None
        if default is not None:
            if default is set:
                processed_default = cast(Set[T], set())
            else:
                processed_default = cast(Set[T], default)

        super().__init__(default=processed_default, **options)
        self.value_field = value_field
        self.min_size = min_size
        self.max_size = max_size

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
        self.value_field.required = True  # Set items can't be None

    async def validate(self, value: Any) -> None:
        """Validate set value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (set, list)):
                raise ValidationError("Value must be a set or list", self.name)

            # Convert to set and cast to correct type
            value_items = cast(Iterable[Any], value)
            value_set = cast(Set[T], set(value_items))

            if self.min_size is not None and len(value_set) < self.min_size:
                raise ValidationError(
                    f"Set must have at least {self.min_size} items",
                    self.name,
                )

            if self.max_size is not None and len(value_set) > self.max_size:
                raise ValidationError(
                    f"Set must have at most {self.max_size} items",
                    self.name,
                )

            # Validate each item
            for item in value_set:
                try:
                    await self.value_field.validate(item)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid item {item!r}: {str(e)}",
                        self.name,
                    )

    async def convert(self, value: Any) -> Optional[Set[T]]:
        """Convert value to set.

        Args:
            value: Value to convert

        Returns:
            Set value

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
            elif not isinstance(value, (set, list)):
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to set",
                    self.name,
                )

            # Convert each item
            result: Set[T] = set()
            value_items = cast(Iterable[Any], value)
            for item in value_items:
                try:
                    converted = await self.value_field.convert(item)
                    if converted is None:
                        raise ValidationError(
                            "Set items cannot be None",
                            self.name,
                        )
                    result.add(converted)
                except ValidationError as e:
                    raise ValidationError(
                        f"Failed to convert item {item!r}: {str(e)}",
                        self.name,
                    )

            return result
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def to_db(self, value: Optional[Set[T]], backend: str) -> Optional[List[Any]]:
        """Convert set to database format.

        Args:
            value: Set value
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        result: List[Any] = []
        value_items = cast(Iterable[T], value)
        for item in value_items:  # Don't sort to avoid comparison issues
            db_value = await self.value_field.to_db(item, backend)
            result.append(db_value)

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[Set[T]]:
        """Convert database value to set.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Set value
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValidationError(
                f"Expected list from database, got {type(value).__name__}",
                self.name,
            )

        value_list = cast(List[Any], value)
        result: Set[T] = set()
        for item in value_list:
            converted = await self.value_field.from_db(item, backend)
            if converted is None:
                raise ValidationError(
                    "Set items cannot be None",
                    self.name,
                )
            result.add(converted)

        return result
