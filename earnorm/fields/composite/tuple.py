"""Tuple field implementation.

This module provides tuple field types for handling fixed-length tuples of values.
It supports:
- Fixed-length tuples with different field types
- Type validation for each position
- Value conversion for each position
- JSON array parsing
- Database conversion

Examples:
    >>> class Point(Model):
    ...     # (x, y) coordinates
    ...     position = TupleField([FloatField(), FloatField()])
    ...     # RGB color values (0-255)
    ...     color = TupleField([
    ...         IntegerField(min_value=0, max_value=255),
    ...         IntegerField(min_value=0, max_value=255),
    ...         IntegerField(min_value=0, max_value=255),
    ...     ])
    ...     # Start and end dates
    ...     date_range = TupleField([DateField(), DateField()])
"""

from typing import Any, List, Optional, Sequence, Tuple, TypeVar, cast

from earnorm.fields.base import Field, ValidationError

T = TypeVar("T")  # Type of tuple items


class TupleField(Field[Tuple[Any, ...]]):
    """Field for fixed-length tuples.

    Attributes:
        fields: List of fields for each position
    """

    def __init__(
        self,
        fields: Sequence[Field[Any]],
        **options: Any,
    ) -> None:
        """Initialize tuple field.

        Args:
            fields: List of fields for each position
            **options: Additional field options
        """
        super().__init__(**options)
        self.fields = list(fields)  # Convert to list for indexing

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

        # Set up field names
        for i, field in enumerate(self.fields):
            field.name = f"{self.name}[{i}]"
            field.required = True  # Tuple items can't be None

    async def validate(self, value: Any) -> None:
        """Validate tuple value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (tuple, list)):
                raise ValidationError("Value must be a tuple or list", self.name)

            value_seq = cast(Sequence[Any], value)
            if len(value_seq) != len(self.fields):
                raise ValidationError(
                    f"Expected {len(self.fields)} items, got {len(value_seq)}",
                    self.name,
                )

            # Validate each item
            for i, (item, field) in enumerate(zip(value_seq, self.fields)):
                try:
                    await field.validate(item)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid item at index {i}: {str(e)}",
                        self.name,
                    )

    async def convert(self, value: Any) -> Optional[Tuple[Any, ...]]:
        """Convert value to tuple.

        Args:
            value: Value to convert

        Returns:
            Tuple value

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
            elif not isinstance(value, (tuple, list)):
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to tuple",
                    self.name,
                )

            # Convert each item
            value_seq = cast(Sequence[Any], value)
            if len(value_seq) != len(self.fields):
                raise ValidationError(
                    f"Expected {len(self.fields)} items, got {len(value_seq)}",
                    self.name,
                )

            result: List[Any] = []
            for i, (item, field) in enumerate(zip(value_seq, self.fields)):
                try:
                    converted = await field.convert(item)
                    if converted is None:
                        raise ValidationError(
                            "Tuple items cannot be None",
                            self.name,
                        )
                    result.append(converted)
                except ValidationError as e:
                    raise ValidationError(
                        f"Failed to convert item at index {i}: {str(e)}",
                        self.name,
                    )

            return tuple(result)
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def to_db(
        self, value: Optional[Tuple[Any, ...]], backend: str
    ) -> Optional[List[Any]]:
        """Convert tuple to database format.

        Args:
            value: Tuple value
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        result: List[Any] = []
        for item, field in zip(value, self.fields):
            db_value = await field.to_db(item, backend)
            result.append(db_value)

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[Tuple[Any, ...]]:
        """Convert database value to tuple.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Tuple value
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValidationError(
                f"Expected list from database, got {type(value).__name__}",
                self.name,
            )

        value_list = cast(List[Any], value)
        if len(value_list) != len(self.fields):
            raise ValidationError(
                f"Expected {len(self.fields)} items, got {len(value_list)}",
                self.name,
            )

        result: List[Any] = []
        for item, field in zip(value_list, self.fields):
            converted = await field.from_db(item, backend)
            if converted is None:
                raise ValidationError(
                    "Tuple items cannot be None",
                    self.name,
                )
            result.append(converted)

        return tuple(result)
