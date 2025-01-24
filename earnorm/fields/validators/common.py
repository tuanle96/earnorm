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
from typing import Any, List, Optional, Sequence, Set, Union
from urllib.parse import urlparse

from earnorm.fields.validators.base import ValidationContext, ValidationError, Validator


class MinLengthValidator(Validator[Union[str, Sequence[Any]]]):
    """Validator for minimum length."""

    def __init__(
        self,
        min_length: int,
        message: Optional[str] = None,
        code: str = "min_length",
    ) -> None:
        """Initialize minimum length validator.

        Args:
            min_length: Minimum length
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.min_length = min_length

    async def validate(
        self, value: Union[str, Sequence[Any]], context: ValidationContext
    ) -> None:
        """Validate value length.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is too short
        """
        if len(value) < self.min_length:
            raise ValidationError(
                message=self.message
                or f"Value must be at least {self.min_length} characters long",
                field_name=context.field.name,
                code=self.code or "min_length",
            )


class MaxLengthValidator(Validator[Union[str, Sequence[Any]]]):
    """Validator for maximum length."""

    def __init__(
        self,
        max_length: int,
        message: Optional[str] = None,
        code: str = "max_length",
    ) -> None:
        """Initialize maximum length validator.

        Args:
            max_length: Maximum length
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.max_length = max_length

    async def validate(
        self, value: Union[str, Sequence[Any]], context: ValidationContext
    ) -> None:
        """Validate value length.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is too long
        """
        if len(value) > self.max_length:
            raise ValidationError(
                message=self.message
                or f"Value must be at most {self.max_length} characters long",
                field_name=context.field.name,
                code=self.code or "max_length",
            )


class PatternValidator(Validator[str]):
    """Validator for pattern matching."""

    def __init__(
        self,
        pattern: Union[str, Pattern[str]],
        message: Optional[str] = None,
        code: str = "invalid_pattern",
    ) -> None:
        """Initialize pattern validator.

        Args:
            pattern: Pattern to match
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.pattern = pattern if isinstance(pattern, Pattern) else re.compile(pattern)

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate value matches pattern.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value doesn't match pattern
        """
        if not self.pattern.match(value):
            raise ValidationError(
                message=self.message
                or f"Value must match pattern {self.pattern.pattern}",
                field_name=context.field.name,
                code=self.code or "invalid_pattern",
            )


class EmailValidator(Validator[str]):
    """Validator for email addresses."""

    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def __init__(
        self,
        message: Optional[str] = None,
        code: str = "invalid_email",
    ) -> None:
        """Initialize email validator.

        Args:
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.pattern = re.compile(self.EMAIL_PATTERN)

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate email address.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is not valid email
        """
        if not self.pattern.match(value):
            raise ValidationError(
                message=self.message or "Invalid email address",
                field_name=context.field.name,
                code=self.code or "invalid_email",
            )


class URLValidator(Validator[str]):
    """Validator for URLs."""

    def __init__(
        self,
        allowed_schemes: Optional[Set[str]] = None,
        message: Optional[str] = None,
        code: str = "invalid_url",
    ) -> None:
        """Initialize URL validator.

        Args:
            allowed_schemes: Set of allowed URL schemes
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.allowed_schemes = allowed_schemes or {"http", "https"}

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate URL.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is not valid URL
        """
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                raise ValidationError(
                    message=self.message or "Invalid URL",
                    field_name=context.field.name,
                    code=self.code or "invalid_url",
                )
            if result.scheme not in self.allowed_schemes:
                raise ValidationError(
                    message=self.message
                    or f"URL scheme must be one of: {', '.join(self.allowed_schemes)}",
                    field_name=context.field.name,
                    code=self.code or "invalid_scheme",
                )
        except Exception as e:
            raise ValidationError(
                message=str(e),
                field_name=context.field.name,
                code=self.code or "invalid_url",
            )


class DateTimeValidator(Validator[datetime]):
    """Validator for datetime values."""

    def __init__(
        self,
        min_value: Optional[datetime] = None,
        max_value: Optional[datetime] = None,
        message: Optional[str] = None,
        code: str = "invalid_datetime",
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
            ValidationError: If value is outside range
        """
        if self.min_value and value < self.min_value:
            raise ValidationError(
                message=self.message or f"Value must be after {self.min_value}",
                field_name=context.field.name,
                code=self.code or "before_min_value",
            )
        if self.max_value and value > self.max_value:
            raise ValidationError(
                message=self.message or f"Value must be before {self.max_value}",
                field_name=context.field.name,
                code=self.code or "after_max_value",
            )


class UniqueValidator(Validator[Sequence[Any]]):
    """Validator for unique values."""

    def __init__(
        self,
        message: Optional[str] = None,
        code: str = "duplicate_values",
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
            ValidationError: If sequence contains duplicates
        """
        seen: Set[Any] = set()
        duplicates: List[Any] = []
        for item in value:
            if item in seen:
                duplicates.append(item)
            seen.add(item)
        if duplicates:
            raise ValidationError(
                message=self.message
                or f"Duplicate values found: {', '.join(str(x) for x in duplicates)}",
                field_name=context.field.name,
                code=self.code or "duplicate_values",
            )
