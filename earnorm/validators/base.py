"""Base validator implementation.

This module provides the base classes and exceptions for all validators in EarnORM.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Optional, Union

# Type alias for validator functions
ValidatorFunc = Callable[[Any], None]
ValidationResult = Union[None, Coroutine[Any, Any, None]]


class ValidationError(Exception):
    """Validation error.

    This exception is raised when validation fails. It contains a message
    describing why the validation failed.

    Examples:
        ```python
        raise ValidationError("Email is invalid")
        raise ValidationError("Value must be positive")
        ```
    """

    def __init__(self, message: str) -> None:
        """Initialize validation error.

        Args:
            message: Error message describing why validation failed
        """
        self.message = message
        super().__init__(message)


class BaseValidator(ABC):
    """Base validator class.

    All validators should inherit from this class and implement the __call__ method.
    The __call__ method should validate the value and raise ValidationError if validation fails.

    Examples:
        ```python
        class EmailValidator(BaseValidator):
            def __call__(self, value: Any) -> None:
                if not isinstance(value, str):
                    raise ValidationError("Value must be a string")
                if "@" not in value:
                    raise ValidationError("Invalid email address")
        ```
    """

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize validator.

        Args:
            message: Custom error message to use when validation fails.
                    If not provided, a default message will be used.
        """
        self.message = message

    @abstractmethod
    def __call__(self, value: Any) -> ValidationResult:
        """Validate value.

        Args:
            value: Value to validate

        Returns:
            None for sync validation, Coroutine for async validation

        Raises:
            ValidationError: If validation fails
        """
        pass


def create_validator(check: Callable[[Any], bool], message: str) -> ValidatorFunc:
    """Create a validator function.

    This is a helper function to create simple validators without defining a new class.
    The check function should return True if validation passes, False otherwise.

    Args:
        check: Function that checks if value is valid
        message: Error message to use when validation fails

    Returns:
        A validator function that raises ValidationError with the given message
        when validation fails

    Examples:
        ```python
        # Create a validator that checks if value is positive
        validate_positive = create_validator(
            lambda x: x > 0,
            "Value must be positive"
        )

        # Use the validator
        validate_positive(5)  # OK
        validate_positive(-1)  # Raises ValidationError
        ```
    """

    def validator(value: Any) -> None:
        if not check(value):
            raise ValidationError(message)

    return validator
