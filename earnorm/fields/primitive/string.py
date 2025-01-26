"""String field implementation.

This module provides string field types for handling text values.
It supports:
- Minimum and maximum length validation
- Regular expression pattern matching
- Case sensitivity options
- String transformations
- Whitespace handling
- Email validation
- URL validation
- Password validation
- Text field with unlimited length

Examples:
    >>> class User(Model):
    ...     name = StringField(min_length=2, max_length=50)
    ...     username = StringField(pattern=r'^[a-z0-9_]+$')
    ...     email = EmailField(required=True)
    ...     password = PasswordField(min_length=8)
    ...     bio = TextField()
"""

import re
from typing import Any, Final, Literal, Optional, Pattern, Union

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import (
    RangeValidator,
    RegexValidator,
    TypeValidator,
    Validator,
)

# Constants
DEFAULT_MIN_LENGTH: Final[Optional[int]] = None
DEFAULT_MAX_LENGTH: Final[Optional[int]] = None
DEFAULT_CASE_SENSITIVE: Final[bool] = True
DEFAULT_STRIP: Final[bool] = True
DEFAULT_TRANSFORM: Final[Optional[Literal["lower", "upper", "title", "capitalize"]]] = (
    None
)

# Password constants
DEFAULT_PASSWORD_MIN_LENGTH: Final[int] = 8
DEFAULT_REQUIRE_UPPER: Final[bool] = True
DEFAULT_REQUIRE_LOWER: Final[bool] = True
DEFAULT_REQUIRE_DIGIT: Final[bool] = True
DEFAULT_REQUIRE_SPECIAL: Final[bool] = True

# URL constants
DEFAULT_REQUIRE_TLD: Final[bool] = True

# Validation patterns
EMAIL_PATTERN: Final[Pattern[str]] = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
URL_PATTERN: Final[Pattern[str]] = re.compile(
    r"^https?://(?:[\w-]+\.)+[\w-]+(?:/[\w-./?%&=]*)?$"
)
PASSWORD_PATTERNS: Final[dict[str, Pattern[str]]] = {
    "upper": re.compile(r"[A-Z]"),
    "lower": re.compile(r"[a-z]"),
    "digit": re.compile(r"\d"),
    "special": re.compile(r"[!@#$%^&*(),.?\":{}|<>]"),
}


class StringField(BaseField[str]):
    """Field for string values.

    This field type handles text values, with support for:
    - Minimum and maximum length validation
    - Regular expression pattern matching
    - Case sensitivity options
    - String transformations
    - Whitespace handling

    Attributes:
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regular expression pattern for validation
        case_sensitive: Whether string matching is case sensitive
        strip: Whether to strip whitespace from input
        transform: String transformation ('lower', 'upper', 'title', 'capitalize')
    """

    min_length: Optional[int]
    max_length: Optional[int]
    pattern: Optional[Pattern[str]]
    case_sensitive: bool
    strip: bool
    transform: Optional[Literal["lower", "upper", "title", "capitalize"]]
    backend_options: dict[str, Any]  # Add type hint for backend_options

    def __init__(
        self,
        *,
        min_length: Optional[int] = DEFAULT_MIN_LENGTH,
        max_length: Optional[int] = DEFAULT_MAX_LENGTH,
        pattern: Optional[Union[str, Pattern[str]]] = None,
        case_sensitive: bool = DEFAULT_CASE_SENSITIVE,
        strip: bool = DEFAULT_STRIP,
        transform: Optional[
            Literal["lower", "upper", "title", "capitalize"]
        ] = DEFAULT_TRANSFORM,
        **options: Any,
    ) -> None:
        """Initialize string field.

        Args:
            min_length: Minimum string length (inclusive)
            max_length: Maximum string length (inclusive)
            pattern: Regular expression pattern for validation
            case_sensitive: Whether string matching is case sensitive
            strip: Whether to strip whitespace from input
            transform: String transformation ('lower', 'upper', 'title', 'capitalize')
            **options: Additional field options
        """
        # Create validators
        field_validators: list[Validator[Any]] = [TypeValidator(str)]
        if min_length is not None or max_length is not None:
            field_validators.append(
                RangeValidator(
                    min_value=min_length,
                    max_value=max_length,
                    message=(
                        f"String length must be between {min_length or 0} "
                        f"and {max_length or 'unlimited'}"
                    ),
                )
            )
        if pattern is not None:
            field_validators.append(
                RegexValidator(
                    str(pattern) if isinstance(pattern, Pattern) else pattern
                )
            )

        super().__init__(validators=field_validators, **options)

        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.case_sensitive = case_sensitive
        self.strip = strip
        self.transform = transform

        # Initialize backend options
        self.backend_options = {
            "mongodb": {
                "type": "string",
                "maxLength": max_length,
            },
            "postgres": {
                "type": "VARCHAR",
                "length": max_length,
            },
            "mysql": {
                "type": "VARCHAR",
                "length": max_length,
            },
        }

    async def validate(self, value: Any) -> None:
        """Validate string value.

        Validates:
        - Type is string
        - Length constraints
        - Pattern matching
        - Required/optional

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: With codes:
                - invalid_type: Value is not a string
                - min_length: String length is less than min_length
                - max_length: String length exceeds max_length
                - invalid_pattern: String does not match pattern

        Examples:
            >>> field = StringField(min_length=2, pattern=r'^[a-z]+$')
            >>> await field.validate("A")  # Raises FieldValidationError(code="min_length")
            >>> await field.validate("Ab")  # Raises FieldValidationError(code="invalid_pattern")
            >>> await field.validate("ab")  # Valid
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, str):
                raise FieldValidationError(
                    message=f"Value must be a string, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.strip:
                value = value.strip()

            if self.min_length is not None and len(value) < self.min_length:
                raise FieldValidationError(
                    message=f"String length must be at least {self.min_length}, got {len(value)}",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value) > self.max_length:
                raise FieldValidationError(
                    message=f"String length must be at most {self.max_length}, got {len(value)}",
                    field_name=self.name,
                    code="max_length",
                )

            if self.pattern is not None:
                if not self.pattern.match(value):
                    raise FieldValidationError(
                        message=f"String must match pattern {self.pattern.pattern}",
                        field_name=self.name,
                        code="invalid_pattern",
                    )

    async def convert(self, value: Any) -> Optional[str]:
        """Convert value to string.

        Handles:
        - None values
        - String conversion
        - Whitespace stripping
        - String transformation

        Args:
            value: Value to convert

        Returns:
            Converted string value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            value = str(value)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to string: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

        if self.strip:
            value = value.strip()

        if self.transform:
            match self.transform:
                case "lower":
                    value = value.lower()
                case "upper":
                    value = value.upper()
                case "title":
                    value = value.title()
                case "capitalize":
                    value = value.capitalize()

        return value

    async def to_db(self, value: Optional[str], backend: str) -> DatabaseValue:
        """Convert string to database format.

        Args:
            value: String value to convert
            backend: Database backend type

        Returns:
            Converted string value or None
        """
        if value is None:
            return None

        if not self.case_sensitive:
            value = value.lower()

        return value

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[str]:
        """Convert database value to string.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted string value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if not isinstance(value, str):
            raise FieldValidationError(
                message=f"Expected string from database, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        return value


class EmailField(StringField):
    """Field for email addresses."""

    def __init__(self, **options: Any) -> None:
        """Initialize email field.

        Args:
            **options: Additional field options
        """
        super().__init__(
            pattern=EMAIL_PATTERN,
            transform="lower",
            strip=True,
            case_sensitive=False,
            **options,
        )


class URLField(StringField):
    """Field for URLs."""

    def __init__(
        self, *, require_tld: bool = DEFAULT_REQUIRE_TLD, **options: Any
    ) -> None:
        """Initialize URL field.

        Args:
            require_tld: Whether to require a top-level domain
            **options: Additional field options
        """
        pattern = (
            URL_PATTERN
            if require_tld
            else URL_PATTERN.pattern.replace(r"\.[a-zA-Z]{2,}", "")
        )
        super().__init__(
            pattern=pattern,
            transform="lower",
            strip=True,
            case_sensitive=False,
            **options,
        )


class PasswordField(StringField):
    """Field for passwords with validation rules."""

    def __init__(
        self,
        *,
        min_length: int = DEFAULT_PASSWORD_MIN_LENGTH,
        require_upper: bool = DEFAULT_REQUIRE_UPPER,
        require_lower: bool = DEFAULT_REQUIRE_LOWER,
        require_digit: bool = DEFAULT_REQUIRE_DIGIT,
        require_special: bool = DEFAULT_REQUIRE_SPECIAL,
        **options: Any,
    ) -> None:
        """Initialize password field.

        Args:
            min_length: Minimum password length
            require_upper: Require uppercase letter
            require_lower: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            **options: Additional field options
        """
        super().__init__(min_length=min_length, strip=True, **options)

        self.require_upper = require_upper
        self.require_lower = require_lower
        self.require_digit = require_digit
        self.require_special = require_special

    async def validate(self, value: Any) -> None:
        """Validate password value.

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if self.require_upper and not PASSWORD_PATTERNS["upper"].search(value):
                raise FieldValidationError(
                    message="Password must contain at least one uppercase letter",
                    field_name=self.name,
                    code="missing_upper",
                )
            if self.require_lower and not PASSWORD_PATTERNS["lower"].search(value):
                raise FieldValidationError(
                    message="Password must contain at least one lowercase letter",
                    field_name=self.name,
                    code="missing_lower",
                )
            if self.require_digit and not PASSWORD_PATTERNS["digit"].search(value):
                raise FieldValidationError(
                    message="Password must contain at least one digit",
                    field_name=self.name,
                    code="missing_digit",
                )
            if self.require_special and not PASSWORD_PATTERNS["special"].search(value):
                raise FieldValidationError(
                    message="Password must contain at least one special character",
                    field_name=self.name,
                    code="missing_special",
                )

    async def to_db(self, value: Optional[str], backend: str) -> Optional[str]:
        """Convert password to database format.

        Args:
            value: Password value to convert
            backend: Database backend type

        Returns:
            Hashed password value or None
        """
        if value is None:
            return None

        # TODO: Implement password hashing
        return value


class TextField(StringField):
    """Field for long text content."""

    def __init__(self, **options: Any) -> None:
        """Initialize text field.

        Args:
            **options: Additional field options
        """
        super().__init__(strip=True, **options)

        # Update backend options for text type
        self.backend_options.update(
            {
                "mongodb": {"type": "string"},
                "postgres": {"type": "TEXT"},
                "mysql": {"type": "TEXT"},
            }
        )
