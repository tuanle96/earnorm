"""String field implementation.

This module provides string field type for handling text data.
It supports:
- String validation
- Length validation
- Pattern matching
- Case sensitivity
- String transformations
- String comparison operations

Examples:
    >>> class User(Model):
    ...     username = StringField(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_]+$')
    ...     email = StringField(pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+[.][a-zA-Z0-9-]+$')
    ...     bio = StringField(max_length=500, nullable=True)
    ...
    ...     # Query examples
    ...     admins = User.find(User.username.starts_with("admin_"))
    ...     gmail = User.find(User.email.ends_with("@gmail.com"))
    ...     has_bio = User.find(User.bio.length_greater_than(0))
"""

import logging
import re
from typing import Any, Final, List, Optional, Union, overload

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import ChoicesValidator, TypeValidator, Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Constants
DEFAULT_MIN_LENGTH: Final[int] = 0
DEFAULT_MAX_LENGTH: Final[Optional[int]] = None
DEFAULT_PATTERN: Final[Optional[str]] = None
DEFAULT_CASE_SENSITIVE: Final[bool] = True
DEFAULT_STRIP: Final[bool] = False
DEFAULT_LOWER: Final[bool] = False
DEFAULT_UPPER: Final[bool] = False


class StringField(BaseField[str], FieldComparisonMixin):
    """Field for string values.

    This field type handles string values, with support for:
    - String validation
    - Length validation
    - Pattern matching
    - Case sensitivity
    - String transformations
    - String comparison operations

    Attributes:
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regular expression pattern
        case_sensitive: Whether string comparison is case sensitive
        strip: Whether to strip whitespace
        lower: Whether to convert to lowercase
        upper: Whether to convert to uppercase
        backend_options: Database backend options
    """

    min_length: int
    max_length: Optional[int]
    pattern: Optional[str]
    case_sensitive: bool
    strip: bool
    lower: bool
    upper: bool
    backend_options: dict[str, Any]

    @overload
    def __get__(self, instance: None, owner: Any) -> "StringField": ...

    @overload
    def __get__(self, instance: Any, owner: Any) -> Optional[str]: ...

    def __get__(
        self, instance: Optional[Any], owner: Any
    ) -> Union["StringField", Optional[str]]:
        """Get field value.

        This method implements the descriptor protocol.
        When accessed through the class, returns the field instance.
        When accessed through an instance, returns the field value.

        Args:
            instance: Model instance or None
            owner: Model class

        Returns:
            Field instance when accessed through class,
            field value when accessed through instance
        """
        if instance is None:
            return self
        return self._value

    def __init__(
        self,
        *,
        min_length: int = DEFAULT_MIN_LENGTH,
        max_length: Optional[int] = DEFAULT_MAX_LENGTH,
        pattern: Optional[str] = DEFAULT_PATTERN,
        case_sensitive: bool = DEFAULT_CASE_SENSITIVE,
        strip: bool = DEFAULT_STRIP,
        lower: bool = DEFAULT_LOWER,
        upper: bool = DEFAULT_UPPER,
        choices: Optional[List[str]] = None,
        **options: Any,
    ) -> None:
        """Initialize string field.

        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regular expression pattern
            case_sensitive: Whether string comparison is case sensitive
            strip: Whether to strip whitespace
            lower: Whether to convert to lowercase
            upper: Whether to convert to uppercase
            choices: List of allowed values
            **options: Additional field options

        Raises:
            ValueError: If length or pattern validation is invalid
        """
        if min_length < 0:
            raise ValueError("min_length must be non-negative")
        if max_length is not None and max_length < min_length:
            raise ValueError("max_length cannot be less than min_length")
        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid pattern: {str(e)}") from e
        if lower and upper:
            raise ValueError("Cannot set both lower and upper to True")

        field_validators: list[Validator[Any]] = [TypeValidator(str)]
        if choices is not None:
            field_validators.append(ChoicesValidator(choices))

        options_without_validators = {
            k: v for k, v in options.items() if k != "validators"
        }
        super().__init__(validators=field_validators, **options_without_validators)

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
            "postgres": {
                "type": f"VARCHAR({max_length})" if max_length is not None else "TEXT"
            },
            "mysql": {
                "type": f"VARCHAR({max_length})" if max_length is not None else "TEXT"
            },
        }

    async def validate(self, value: Any) -> None:
        """Validate string value.

        Args:
            value: String value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        logger = logging.getLogger(__name__)

        if value is None:
            if self.required:
                raise FieldValidationError(
                    message=f"{self.name} is required",
                    field_name=self.name,
                    code="required",
                )
            return

        # Convert bytes to string if needed
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError:
                raise FieldValidationError(
                    message=f"{self.name} contains invalid UTF-8 bytes",
                    field_name=self.name,
                    code="invalid_encoding",
                )
        elif not isinstance(value, str):
            raise FieldValidationError(
                message=f"{self.name} must be a string, got {type(value)}",
                field_name=self.name,
                code="invalid_type",
            )

        # Length validation
        length = len(value)
        if self.min_length and length < self.min_length:
            raise FieldValidationError(
                message=f"{self.name}: String length {length} is less than minimum {self.min_length}",
                field_name=self.name,
                code="min_length",
            )

        if self.max_length and length > self.max_length:
            raise FieldValidationError(
                message=f"{self.name}: String length {length} is greater than maximum {self.max_length}",
                field_name=self.name,
                code="max_length",
            )

        # Pattern validation
        if self.pattern:
            logger.debug(f"Validating pattern for {self.name}")
            logger.debug(f"Value: '{value}'")
            logger.debug(f"Pattern: '{self.pattern}'")

            match = re.match(self.pattern, str(value))
            logger.debug(f"Pattern match result: {match}")

            if not match:
                raise FieldValidationError(
                    message=f"{self.name}: String does not match pattern: {self.pattern}",
                    field_name=self.name,
                    code="pattern",
                )

    async def convert(self, value: Any) -> Optional[str]:
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
                message=f"Cannot convert value to string: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[str], backend: str) -> DatabaseValue:
        """Convert string to database format.

        Args:
            value: String value to convert
            backend: Database backend type

        Returns:
            Converted string value or None
        """
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

        try:
            if isinstance(value, str):
                return value
            return str(value)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to string: {str(e)}",
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
        return ComparisonOperator(
            self.name, "not_contains", self._prepare_value(substring)
        )

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
