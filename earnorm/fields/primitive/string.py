"""String field implementation.

This module provides string field types for storing text data.
It includes:
- Basic string field
- Email field with validation
- URL field with validation
- Password field with hashing
"""

import re
from re import Pattern
from typing import Any, Final

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import ChoicesValidator, TypeValidator, Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Constants
DEFAULT_MIN_LENGTH: Final[int] = 0
DEFAULT_MAX_LENGTH: Final[int | None] = None
DEFAULT_PATTERN: Final[str | None] = None
DEFAULT_CASE_SENSITIVE: Final[bool] = True
DEFAULT_STRIP: Final[bool] = False
DEFAULT_LOWER: Final[bool] = False
DEFAULT_UPPER: Final[bool] = False


class StringField(BaseField[str], FieldComparisonMixin):
    """Field for storing string values.

    This field handles:
    - Basic string validation
    - Length constraints
    - Pattern matching
    - Case sensitivity options

    Examples:
        >>> class User(BaseModel):
        ...     name = StringField(required=True, min_length=2)
        ...     email = StringField(pattern='[^@]+@[^@]+[.][@]+')
        ...     bio = StringField(max_length=1000)
    """

    field_type = "string"  # Database field type
    python_type = str  # Python type

    min_length: int | None
    max_length: int | None
    pattern: str | Pattern[str] | None
    case_sensitive: bool
    strip: bool
    lower: bool
    upper: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | Pattern[str] | None = None,
        case_sensitive: bool = True,
        strip: bool = False,
        lower: bool = False,
        upper: bool = False,
        choices: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize string field.

        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regular expression pattern to validate against
            case_sensitive: Whether string comparisons are case sensitive
            strip: Whether to strip whitespace
            lower: Whether to convert to lowercase
            upper: Whether to convert to uppercase
            choices: List of allowed values
            **kwargs: Additional field options
        """
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.case_sensitive = case_sensitive
        self.strip = strip
        self.lower = lower
        self.upper = upper

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "string"},
            "postgres": {"type": f"VARCHAR({max_length})" if max_length is not None else "TEXT"},
            "mysql": {"type": f"VARCHAR({max_length})" if max_length is not None else "TEXT"},
        }

        # Validate min_length and max_length
        if min_length is not None:
            if min_length < 0:
                raise ValueError("min_length must be non-negative")
            if max_length is not None and max_length < min_length:
                raise ValueError("max_length cannot be less than min_length")

        # Validate pattern
        if pattern is not None:
            try:
                if isinstance(pattern, Pattern):
                    re.compile(pattern)
                else:
                    re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid pattern: {e!s}") from e

        if lower and upper:
            raise ValueError("Cannot set both lower and upper to True")

        field_validators: list[Validator[Any]] = [TypeValidator(str)]
        if choices is not None:
            field_validators.append(ChoicesValidator(choices))

        options_without_validators = {k: v for k, v in kwargs.items() if k != "validators"}
        super().__init__(validators=field_validators, **options_without_validators)

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> Any:
        """Validate string value.

        This method checks:
        - Basic string validation from parent
        - Length constraints
        - Pattern matching if specified

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Any: The validated value

        Raises:
            ValidationError: If validation fails
        """
        value = await super().validate(value, context)
        if value is None:
            return None

        # Validate length
        if self.min_length is not None and len(value) < self.min_length:
            raise ValueError(f"String length must be at least {self.min_length} characters")
        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"String length must be at most {self.max_length} characters")

        # Validate pattern
        if self.pattern:
            pattern = self.pattern if isinstance(self.pattern, Pattern) else re.compile(self.pattern)
            if not pattern.match(value):
                raise ValueError("String does not match required pattern")

        return value

    async def convert(self, value: Any) -> str | None:
        """Convert value to string.

        Handles:
        - None values
        - String values
        - Values with __str__ method

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
            result = str(value)

            # Apply transformations
            if self.strip:
                result = result.strip()
            if self.lower:
                result = result.lower()
            if self.upper:
                result = result.upper()

            return result
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to string: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: str | None, backend: str) -> DatabaseValue:
        """Convert string to database format.

        Args:
            value: String value to convert
            backend: Database backend type

        Returns:
            Converted string value or None
        """
        return value

    async def from_db(self, value: DatabaseValue, backend: str) -> str | None:
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

        try:
            if isinstance(value, str):
                return value
            return str(value)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to string: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare string value for comparison.

        Converts value to string and applies case sensitivity.

        Args:
            value: Value to prepare

        Returns:
            Prepared string value or None
        """
        if value is None:
            return None

        try:
            result = str(value)
            if not self.case_sensitive:
                result = result.lower()
            return result
        except (TypeError, ValueError):
            return None

    def equals(self, value: str) -> ComparisonOperator:
        """Check if value equals another string.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "eq", self._prepare_value(value))

    def not_equals(self, value: str) -> ComparisonOperator:
        """Check if value does not equal another string.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "ne", self._prepare_value(value))

    def contains(self, substring: str) -> ComparisonOperator:
        """Check if string contains substring.

        Args:
            substring: Substring to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(substring))

    def not_contains(self, substring: str) -> ComparisonOperator:
        """Check if string does not contain substring.

        Args:
            substring: Substring to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_contains", self._prepare_value(substring))

    def starts_with(self, prefix: str) -> ComparisonOperator:
        """Check if string starts with prefix.

        Args:
            prefix: Prefix to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "starts_with", self._prepare_value(prefix))

    def ends_with(self, suffix: str) -> ComparisonOperator:
        """Check if string ends with suffix.

        Args:
            suffix: Suffix to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "ends_with", self._prepare_value(suffix))

    def matches(self, pattern: str) -> ComparisonOperator:
        """Check if string matches regular expression pattern.

        Args:
            pattern: Regular expression pattern

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "matches", pattern)

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if string length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if string length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if string length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

    def in_list(self, values: list[str]) -> ComparisonOperator:
        """Check if value is in list of strings.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "in", prepared_values)

    def not_in_list(self, values: list[str]) -> ComparisonOperator:
        """Check if value is not in list of strings.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "not_in", prepared_values)

    def is_empty(self) -> ComparisonOperator:
        """Check if string is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if string is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
