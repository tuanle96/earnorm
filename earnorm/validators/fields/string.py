"""String field validators.

This module provides validators for string fields, including:
- Email validation
- URL validation
- IP address validation
- Regex pattern validation
- Length validation
- Choice validation
"""

import re
from collections.abc import Sequence
from typing import Any

from earnorm.types import ValidatorFunc
from earnorm.validators.base import BaseValidator, ValidationError, create_validator


class EmailValidator(BaseValidator):
    """Email address validator.

    Examples:
        ```python
        # Create validator
        validate_email = EmailValidator()

        # Use validator
        validate_email("user@example.com")  # OK
        validate_email("invalid")  # Raises ValidationError
        ```
    """

    def __call__(self, value: Any) -> None:
        """Validate email address.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is not a valid email address
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if not value:
            raise ValidationError("Email is required")

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, value):
            raise ValidationError(self.message or "Invalid email address")


class URLValidator(BaseValidator):
    """URL validator.

    Examples:
        ```python
        # Create validator
        validate_url = URLValidator()

        # Use validator
        validate_url("https://example.com")  # OK
        validate_url("invalid")  # Raises ValidationError
        ```
    """

    def __call__(self, value: Any) -> None:
        """Validate URL.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is not a valid URL
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if not value:
            raise ValidationError("URL is required")

        pattern = r"^https?://(?:[\w-]+\.)+[\w-]+(?:/[\w-./?%&=]*)?$"
        if not re.match(pattern, value):
            raise ValidationError(self.message or "Invalid URL")


class IPValidator(BaseValidator):
    """IP address validator.

    Examples:
        ```python
        # Create validator
        validate_ip = IPValidator()

        # Use validator
        validate_ip("192.168.1.1")  # OK
        validate_ip("invalid")  # Raises ValidationError
        ```
    """

    def __call__(self, value: Any) -> None:
        """Validate IP address.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is not a valid IP address
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if not value:
            raise ValidationError("IP address is required")

        pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if not re.match(pattern, value):
            raise ValidationError(self.message or "Invalid IP address")


class RegexValidator(BaseValidator):
    """Regex pattern validator.

    Examples:
        ```python
        # Create validator
        validate_pattern = RegexValidator(r"^[a-z]+$")

        # Use validator
        validate_pattern("abc")  # OK
        validate_pattern("123")  # Raises ValidationError
        ```
    """

    def __init__(self, pattern: str | re.Pattern[str], message: str | None = None) -> None:
        """Initialize validator.

        Args:
            pattern: Regex pattern to match against
            message: Custom error message
        """
        super().__init__(message)
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    def __call__(self, value: Any) -> None:
        """Validate value against regex pattern.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value does not match pattern
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if not self.pattern.match(value):
            raise ValidationError(self.message or "Value does not match pattern")


def validate_length(
    min_length: int | None = None,
    max_length: int | None = None,
    message: str | None = None,
) -> ValidatorFunc:
    """Create length validator.

    Args:
        min_length: Minimum length allowed
        max_length: Maximum length allowed
        message: Custom error message

    Returns:
        Validator function that checks string length

    Examples:
        ```python
        # Create validator
        validate_name = validate_length(min_length=2, max_length=50)

        # Use validator
        validate_name("John")  # OK
        validate_name("A")  # Raises ValidationError
        ```
    """

    def validator(value: Any) -> None:  # type: ignore
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if min_length is not None and len(value) < min_length:
            raise ValidationError(message or f"Length must be at least {min_length}")
        if max_length is not None and len(value) > max_length:
            raise ValidationError(message or f"Length must be at most {max_length}")

    return validator


def validate_choice(choices: Sequence[str], message: str | None = None) -> ValidatorFunc:
    """Create choice validator.

    Args:
        choices: Valid choices
        message: Custom error message

    Returns:
        Validator function that checks if value is in choices

    Examples:
        ```python
        # Create validator
        validate_status = validate_choice(["active", "inactive"])

        # Use validator
        validate_status("active")  # OK
        validate_status("pending")  # Raises ValidationError
        ```
    """
    return create_validator(
        lambda x: isinstance(x, str) and x in choices,
        message or f"Value must be one of: {', '.join(choices)}",
    )


def validate_regex(pattern: str | re.Pattern[str], message: str | None = None) -> ValidatorFunc:
    """Create regex validator.

    Args:
        pattern: Regex pattern to match against
        message: Custom error message

    Returns:
        Validator function that checks if value matches pattern

    Examples:
        ```python
        # Create validator
        validate_alpha = validate_regex(r"^[a-z]+$")

        # Use validator
        validate_alpha("abc")  # OK
        validate_alpha("123")  # Raises ValidationError
        ```
    """
    return RegexValidator(pattern, message)
