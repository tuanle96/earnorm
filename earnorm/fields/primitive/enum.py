"""Enum field implementation.

This module provides enum field type for handling enumerated values.
It supports:
- Enum validation
- String/integer conversion
- Case sensitivity control
- Database type mapping

Examples:
    >>> from enum import Enum
    >>> class UserStatus(Enum):
    ...     ACTIVE = "active"
    ...     INACTIVE = "inactive"
    ...     BANNED = "banned"
    ...
    >>> class User(Model):
    ...     status = EnumField(UserStatus, default=UserStatus.ACTIVE)
    ...     role = EnumField(UserRole, required=True)
"""

from enum import Enum
from typing import Any, Final, Generic, Optional, Type, TypeVar

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import TypeValidator, Validator

# Type variable for enum type
E = TypeVar("E", bound=Enum)

# Constants
DEFAULT_CASE_SENSITIVE: Final[bool] = True


class EnumField(BaseField[E], Generic[E]):
    """Field for enum values.

    This field type handles enumerated values, with support for:
    - Enum validation
    - String/integer conversion
    - Case sensitivity control
    - Database type mapping

    Attributes:
        enum_class: Enum class to use
        case_sensitive: Whether string comparison is case sensitive
        backend_options: Database backend options
    """

    enum_class: Type[E]
    case_sensitive: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        enum_class: Type[E],
        *,
        case_sensitive: bool = DEFAULT_CASE_SENSITIVE,
        **options: Any,
    ) -> None:
        """Initialize enum field.

        Args:
            enum_class: Enum class to use
            case_sensitive: Whether string comparison is case sensitive
            **options: Additional field options

        Raises:
            TypeError: If enum_class is not an Enum class
        """
        if not isinstance(enum_class, type):
            raise TypeError(f"{enum_class} is not an Enum class")

        field_validators: list[Validator[Any]] = [TypeValidator(enum_class)]
        super().__init__(validators=field_validators, **options)

        self.enum_class = enum_class
        self.case_sensitive = case_sensitive

        # Get the type of enum values
        first_value = next(iter(enum_class.__members__.values())).value
        value_type = (
            str
            if isinstance(first_value, str)
            else int if isinstance(first_value, int) else object
        )

        # Initialize backend options based on value type
        if value_type == str:
            max_length = max(len(str(v.value)) for v in enum_class.__members__.values())
            self.backend_options = {
                "mongodb": {"type": "string"},
                "postgres": {"type": f"VARCHAR({max_length})"},
                "mysql": {"type": f"VARCHAR({max_length})"},
            }
        elif value_type == int:
            self.backend_options = {
                "mongodb": {"type": "int"},
                "postgres": {"type": "INTEGER"},
                "mysql": {"type": "INTEGER"},
            }
        else:
            self.backend_options = {
                "mongodb": {"type": "string"},
                "postgres": {"type": "TEXT"},
                "mysql": {"type": "TEXT"},
            }

    async def validate(self, value: Any) -> None:
        """Validate enum value.

        This method validates:
        - Value is an instance of enum_class
        - Value is one of the allowed enum values

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, self.enum_class):
                raise FieldValidationError(
                    message=(
                        f"Value must be an instance of {self.enum_class.__name__}, "
                        f"got {type(value).__name__}"
                    ),
                    field_name=self.name,
                    code="invalid_type",
                )

            if value not in self.enum_class.__members__.values():
                raise FieldValidationError(
                    message=(
                        f"Invalid enum value: {value}. "
                        f"Allowed values: {list(self.enum_class.__members__.values())}"
                    ),
                    field_name=self.name,
                    code="invalid_choice",
                )

    async def convert(self, value: Any) -> Optional[E]:
        """Convert value to enum.

        Handles:
        - None values
        - Enum instances
        - String values (names or values)
        - Integer values (for integer enums)

        Args:
            value: Value to convert

        Returns:
            Converted enum value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, self.enum_class):
                return value

            # Try to convert from string
            if isinstance(value, str):
                # Try by name
                try:
                    if self.case_sensitive:
                        return self.enum_class[value]
                    else:
                        upper_value = value.upper()
                        for name, member in self.enum_class.__members__.items():
                            if name.upper() == upper_value:
                                return member
                        raise KeyError(value)
                except KeyError:
                    # Try by value
                    for member in self.enum_class.__members__.values():
                        member_value = str(member.value)
                        if (
                            self.case_sensitive
                            and member_value == value
                            or not self.case_sensitive
                            and member_value.upper() == value.upper()
                        ):
                            return member

            # Try to convert from integer
            if isinstance(value, int):
                for member in self.enum_class.__members__.values():
                    if member.value == value:
                        return member

            raise ValueError(
                f"Cannot convert {value} to {self.enum_class.__name__}. "
                f"Allowed values: {list(self.enum_class.__members__.values())}"
            )
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[E], backend: str) -> DatabaseValue:
        """Convert enum to database format.

        Args:
            value: Enum value to convert
            backend: Database backend type

        Returns:
            Converted enum value or None
        """
        if value is None:
            return None

        return value.value

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[E]:
        """Convert database value to enum.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted enum value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            for member in self.enum_class.__members__.values():
                if member.value == value:
                    return member

            raise ValueError(
                f"Cannot convert database value {value} to {self.enum_class.__name__}. "
                f"Allowed values: {list(self.enum_class.__members__.values())}"
            )
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e
