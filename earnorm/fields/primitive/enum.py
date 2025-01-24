"""Enum field type.

This module provides the EnumField class for handling enumeration values.
It supports:
- Enum validation and conversion
- String/value conversion to enum
- Case-insensitive enum lookup
- Default value handling
- Database backend support
- Custom validation

Examples:
    >>> from enum import Enum
    >>> class Status(Enum):
    ...     ACTIVE = "active"
    ...     INACTIVE = "inactive"
    ...     PENDING = "pending"

    >>> class User(Model):
    ...     status = EnumField(Status, default=Status.INACTIVE)
    ...     role = EnumField(UserRole, required=True)

    >>> user = User()
    >>> user.status = "active"  # Converts to Status.ACTIVE
    >>> user.status = Status.PENDING  # Direct enum assignment
    >>> user.role = "invalid"  # Raises ValidationError
"""

from enum import Enum
from typing import Any, List, Optional, Type, TypeVar, Union

from earnorm.fields.base import Field, ValidationError

# Type alias for validator functions
ValidatorFunc = Any  # Temporary fix until we can import from validators.types

E = TypeVar("E", bound=Enum)


class EnumField(Field[E]):
    """Enum field type.

    This field handles:
    - Enum validation and conversion
    - String/value conversion to enum
    - Case-insensitive lookup
    - Database serialization

    Attributes:
        required: Whether field is required
        unique: Whether field value must be unique
        enum_class: The Enum class to use
        default: Default enum value

    Raises:
        ValidationError: With codes:
            - invalid_value: Value cannot be converted to enum
            - required: Value is required but None
    """

    def __init__(
        self,
        enum_class: Type[E],
        *,
        required: bool = False,
        unique: bool = False,
        default: Optional[Union[E, str, Any]] = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize enum field.

        Args:
            enum_class: The Enum class to use
            required: Whether field is required (defaults to False)
            unique: Whether field value must be unique (defaults to False)
            default: Default value (defaults to first enum value)
            validators: List of validator functions
            **kwargs: Additional field options

        Examples:
            >>> field = EnumField(Status)  # Uses first enum value as default
            >>> field = EnumField(Status, default=Status.INACTIVE)  # Custom default
            >>> field = EnumField(Status, required=True)  # Required field
        """
        # Convert default value if provided as string
        if isinstance(default, str):
            try:
                default = enum_class(default)
            except ValueError:
                try:
                    default = enum_class[default.upper()]
                except KeyError:
                    raise ValueError(
                        f"Invalid default value for enum {enum_class.__name__}: {default}"
                    )

        # Get default value from enum if not provided
        default_value = default if default is not None else next(iter(enum_class))

        # Initialize base class
        super().__init__(
            required=required,
            unique=unique,
            default=default_value,
            validators=validators,
            **kwargs,
        )
        self.enum_class = enum_class
        self._default_value = default_value

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "string",
                    "enum": [e.value for e in enum_class],
                },
                "postgres": {
                    "type": "VARCHAR",
                    "check": f"CHECK ({self.name} IN ({', '.join(repr(e.value) for e in enum_class)}))",
                },
                "mysql": {
                    "type": "ENUM",
                    "values": [e.value for e in enum_class],
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate enum value.

        Validates:
        - Value is valid enum type
        - Value can be converted to enum
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a valid enum type
                - invalid_value: Value cannot be converted to enum
                - required: Value is required but None

        Examples:
            >>> field = EnumField(Status)
            >>> await field.validate(Status.ACTIVE)  # Valid
            >>> await field.validate("active")  # Valid
            >>> await field.validate("invalid")  # Raises ValidationError
            >>> await field.validate(None)  # Valid if not required
        """
        await super().validate(value)

        if value is not None:
            try:
                if not isinstance(value, self.enum_class):
                    await self.convert(value)  # Try converting
            except (ValueError, KeyError) as e:
                valid_values = ", ".join(
                    f"{e.name}={e.value!r}" for e in self.enum_class
                )
                raise ValidationError(
                    message=f"Invalid value for enum {self.enum_class.__name__}: {value!r}. Valid values are: {valid_values}",
                    field_name=self.name,
                    code="invalid_value",
                ) from e

    async def convert(self, value: Any) -> E:
        """Convert value to enum.

        Handles:
        - None values (returns default)
        - Enum values (returned as is)
        - String values (case-insensitive lookup)
        - Raw values (direct enum lookup)

        Args:
            value: Value to convert

        Returns:
            Converted enum value

        Raises:
            ValidationError: With code "invalid_value" if value cannot be converted

        Examples:
            >>> field = EnumField(Status)
            >>> await field.convert(None)  # Returns default value
            >>> await field.convert(Status.ACTIVE)  # Returns Status.ACTIVE
            >>> await field.convert("active")  # Returns Status.ACTIVE
            >>> await field.convert("ACTIVE")  # Returns Status.ACTIVE
            >>> await field.convert("invalid")  # Raises ValidationError
        """
        if value is None:
            return self._default_value  # type: ignore[return-value]

        if isinstance(value, self.enum_class):
            return value

        try:
            # First try direct value lookup
            enum_value = self.enum_class(value)
            if not isinstance(enum_value, self.enum_class):
                raise ValueError("Invalid enum value")
            return enum_value  # type: ignore[return-value]
        except ValueError:
            try:
                # Then try case-insensitive name lookup
                enum_value = self.enum_class[str(value).upper()]
                if not isinstance(enum_value, self.enum_class):
                    raise ValueError("Invalid enum value")
                return enum_value  # type: ignore[return-value]
            except KeyError as e:
                valid_values = ", ".join(
                    f"{e.name}={e.value!r}" for e in self.enum_class
                )
                raise ValidationError(
                    message=f"Cannot convert {value!r} to enum {self.enum_class.__name__}. Valid values are: {valid_values}",
                    field_name=self.name,
                    code="invalid_value",
                ) from e

    async def to_db(self, value: Optional[E], backend: str) -> Optional[str]:
        """Convert enum to database format.

        Args:
            value: Enum value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database string value or None

        Examples:
            >>> field = EnumField(Status)
            >>> await field.to_db(Status.ACTIVE, "mongodb")  # Returns "active"
            >>> await field.to_db(None, "postgres")  # Returns None
        """
        if value is None:
            return None
        return value.value

    async def from_db(self, value: Any, backend: str) -> E:
        """Convert database value to enum.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted enum value

        Raises:
            ValidationError: With code "invalid_value" if value cannot be converted

        Examples:
            >>> field = EnumField(Status)
            >>> await field.from_db("active", "mongodb")  # Returns Status.ACTIVE
            >>> await field.from_db(None, "postgres")  # Returns default value
            >>> await field.from_db("invalid", "mysql")  # Raises ValidationError
        """
        if value is None:
            return self._default_value  # type: ignore[return-value]

        try:
            enum_value = self.enum_class(value)
            if not isinstance(enum_value, self.enum_class):
                raise ValueError("Invalid enum value")
            return enum_value  # type: ignore[return-value]
        except ValueError as e:
            valid_values = ", ".join(f"{e.name}={e.value!r}" for e in self.enum_class)
            raise ValidationError(
                message=f"Cannot convert database value {value!r} to enum {self.enum_class.__name__}. Valid values are: {valid_values}",
                field_name=self.name,
                code="invalid_value",
            ) from e
