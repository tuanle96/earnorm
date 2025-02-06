"""Common field validators implementation.

This module provides common validators for field validation.
It supports:
- Length validation
- Pattern matching
- Email validation
- URL validation
- Date/time validation
- Uniqueness validation

Examples:
    >>> field = StringField(
    ...     validators=[
    ...         MinLengthValidator(5),
    ...         PatternValidator(r"^[a-z]+$"),
    ...     ]
    ... )
"""

import re
from datetime import datetime
from re import Pattern
from typing import (
    Any,
    Final,
    FrozenSet,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    TypeGuard,
    TypeVar,
    Union,
    final,
)
from urllib.parse import urlparse

from earnorm.exceptions import FieldValidationError
from earnorm.fields.validators.base import ValidationContext, Validator

# Type variables with constraints
S = TypeVar("S", str, Sequence[Any])
T = TypeVar("T")


class LengthProtocol(Protocol):
    """Protocol for objects that support len()."""

    def __len__(self) -> int: ...


@final
class MinLengthValidator(Validator[S]):
    """Validator for minimum length."""

    DEFAULT_CODE: Final[str] = "min_length"

    def __init__(
        self,
        min_length: int,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize minimum length validator.

        Args:
            min_length: Minimum length
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.min_length: int = min_length

    async def validate(self, value: S, context: ValidationContext) -> None:
        """Validate value length.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is too short
        """
        if len(value) < self.min_length:
            raise FieldValidationError(
                message=self.message
                or f"Value must be at least {self.min_length} characters long",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


@final
class MaxLengthValidator(Validator[S]):
    """Validator for maximum length."""

    DEFAULT_CODE: Final[str] = "max_length"

    def __init__(
        self,
        max_length: int,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize maximum length validator.

        Args:
            max_length: Maximum length
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.max_length: int = max_length

    async def validate(self, value: S, context: ValidationContext) -> None:
        """Validate value length.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is too long
        """
        if len(value) > self.max_length:
            raise FieldValidationError(
                message=self.message
                or f"Value must be at most {self.max_length} characters long",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


@final
class PatternValidator(Validator[str]):
    """Validator for pattern matching."""

    DEFAULT_CODE: Final[str] = "invalid_pattern"

    def __init__(
        self,
        pattern: Union[str, Pattern[str]],
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize pattern validator.

        Args:
            pattern: Pattern to match
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.pattern: Pattern[str] = (
            pattern if isinstance(pattern, Pattern) else re.compile(pattern)
        )

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate value matches pattern.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value doesn't match pattern
        """
        if not self.pattern.match(value):
            raise FieldValidationError(
                message=self.message
                or f"Value must match pattern {self.pattern.pattern}",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


@final
class EmailValidator(Validator[str]):
    """Validator for email addresses."""

    EMAIL_PATTERN: Final[str] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    DEFAULT_CODE: Final[str] = "invalid_email"

    def __init__(
        self,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize email validator.

        Args:
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.pattern: Pattern[str] = re.compile(self.EMAIL_PATTERN)

    def is_valid_email(self, value: str) -> TypeGuard[str]:
        """Check if value is valid email.

        Args:
            value: Value to check

        Returns:
            True if value is valid email
        """
        return bool(self.pattern.match(value))

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate email address.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is not valid email
        """
        if not self.is_valid_email(value):
            raise FieldValidationError(
                message=self.message or "Invalid email address",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


@final
class URLValidator(Validator[str]):
    """Validator for URLs."""

    DEFAULT_SCHEMES: Final[FrozenSet[str]] = frozenset({"http", "https"})
    DEFAULT_CODE: Final[str] = "invalid_url"

    def __init__(
        self,
        allowed_schemes: Optional[Set[str]] = None,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize URL validator.

        Args:
            allowed_schemes: Set of allowed URL schemes
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.allowed_schemes: FrozenSet[str] = frozenset(
            allowed_schemes or self.DEFAULT_SCHEMES
        )

    def is_valid_url(self, value: str) -> TypeGuard[str]:
        """Check if value is valid URL.

        Args:
            value: Value to check

        Returns:
            True if value is valid URL
        """
        try:
            result = urlparse(value)
            return bool(
                result.scheme
                and result.netloc
                and result.scheme in self.allowed_schemes
            )
        except Exception:
            return False

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate URL.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is not valid URL
        """
        if not self.is_valid_url(value):
            raise FieldValidationError(
                message=self.message
                or f"Invalid URL. Allowed schemes: {', '.join(sorted(self.allowed_schemes))}",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


class DateTimeValidator(Validator[datetime]):
    """Validator for datetime values."""

    DEFAULT_CODE: Final[str] = "invalid_datetime"

    def __init__(
        self,
        min_value: Optional[datetime] = None,
        max_value: Optional[datetime] = None,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize datetime validator.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.min_value = min_value
        self.max_value = max_value

    async def validate(self, value: datetime, context: ValidationContext) -> None:
        """Validate datetime value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is outside range
        """
        if self.min_value and value < self.min_value:
            raise FieldValidationError(
                message=self.message or f"Value must be after {self.min_value}",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )
        if self.max_value and value > self.max_value:
            raise FieldValidationError(
                message=self.message or f"Value must be before {self.max_value}",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )


class UniqueValidator(Validator[Sequence[Any]]):
    """Validator for unique values."""

    DEFAULT_CODE: Final[str] = "duplicate_values"

    def __init__(
        self,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize unique validator.

        Args:
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)

    async def validate(self, value: Sequence[Any], context: ValidationContext) -> None:
        """Validate sequence contains no duplicates.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If sequence contains duplicates
        """
        seen: Set[Any] = set()
        duplicates: List[Any] = []
        for item in value:
            if item in seen:
                duplicates.append(item)
            seen.add(item)
        if duplicates:
            raise FieldValidationError(
                message=self.message
                or f"Duplicate values found: {', '.join(str(x) for x in duplicates)}",
                field_name=getattr(context.field, "name", "unknown"),
                code=self.code or self.DEFAULT_CODE,
            )
