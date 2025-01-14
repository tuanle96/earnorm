"""Base validator implementation."""

import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Pattern, TypeVar, Union

T = TypeVar("T")


class ValidationError(Exception):
    """Validation error."""

    def __init__(self, message: str) -> None:
        """Initialize validation error.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)


class BaseValidator(ABC):
    """Base validator class."""

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize validator.

        Args:
            message: Custom error message
        """
        self.message = message

    @abstractmethod
    def __call__(self, value: Any) -> None:
        """Validate value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        pass


def validate_email(value: str) -> None:
    """Validate email address.

    Args:
        value: Email address to validate

    Raises:
        ValidationError: If email is invalid
    """
    if not value:
        raise ValidationError("Email is required")

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, value):
        raise ValidationError("Invalid email address")


def validate_length(
    min_length: Optional[int] = None, max_length: Optional[int] = None
) -> Callable[[str], None]:
    """Create length validator.

    Args:
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        Validator function
    """

    def validator(value: str) -> None:
        if min_length is not None and len(value) < min_length:
            raise ValidationError(f"Length must be at least {min_length}")
        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"Length must be at most {max_length}")

    return validator


def validate_range(
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
) -> Callable[[Union[int, float]], None]:
    """Create range validator.

    Args:
        min_value: Minimum value
        max_value: Maximum value

    Returns:
        Validator function
    """

    def validator(value: Union[int, float]) -> None:
        if min_value is not None and value < min_value:
            raise ValidationError(f"Value must be at least {min_value}")
        if max_value is not None and value > max_value:
            raise ValidationError(f"Value must be at most {max_value}")

    return validator


def validate_regex(pattern: Union[str, Pattern[str]]) -> Callable[[str], None]:
    """Create regex validator.

    Args:
        pattern: Regex pattern

    Returns:
        Validator function
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)

    def validator(value: str) -> None:
        if not pattern.match(value):
            raise ValidationError("Value does not match pattern")

    return validator
