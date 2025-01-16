"""Number field validators.

This module provides validators for number fields, including:
- Range validation
- Min/max value validation
- Positive/negative validation
- Zero validation
"""

from decimal import Decimal
from typing import Any, Optional, Union

from earnorm.validators.base import BaseValidator, ValidationError, create_validator
from earnorm.validators.types import ValidatorFunc

# Type alias for number types
Number = Union[int, float, Decimal]


class RangeValidator(BaseValidator):
    """Range validator.

    Examples:
        ```python
        # Create validator
        validate_range = RangeValidator(min_value=0, max_value=100)

        # Use validator
        validate_range(50)  # OK
        validate_range(-1)  # Raises ValidationError
        validate_range(101)  # Raises ValidationError
        ```
    """

    def __init__(
        self,
        min_value: Optional[Number] = None,
        max_value: Optional[Number] = None,
        message: Optional[str] = None,
    ) -> None:
        """Initialize validator.

        Args:
            min_value: Minimum value allowed
            max_value: Maximum value allowed
            message: Custom error message
        """
        super().__init__(message)
        self.min_value = float(min_value) if min_value is not None else None
        self.max_value = float(max_value) if max_value is not None else None

    def __call__(self, value: Any) -> None:
        """Validate value is within range.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If value is not within range
        """
        if not isinstance(value, (int, float, Decimal)):
            raise ValidationError("Value must be a number")

        value = float(value)

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                self.message or f"Value must be at least {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                self.message or f"Value must be at most {self.max_value}"
            )


def validate_min(min_value: Number, message: Optional[str] = None) -> ValidatorFunc:
    """Create minimum value validator.

    Args:
        min_value: Minimum value allowed
        message: Custom error message

    Returns:
        Validator function that checks minimum value

    Examples:
        ```python
        # Create validator
        validate_positive = validate_min(0)

        # Use validator
        validate_positive(5)  # OK
        validate_positive(-1)  # Raises ValidationError
        ```
    """
    min_value = float(min_value)
    return create_validator(
        lambda x: isinstance(x, (int, float, Decimal)) and float(x) >= min_value,
        message or f"Value must be at least {min_value}",
    )


def validate_max(max_value: Number, message: Optional[str] = None) -> ValidatorFunc:
    """Create maximum value validator.

    Args:
        max_value: Maximum value allowed
        message: Custom error message

    Returns:
        Validator function that checks maximum value

    Examples:
        ```python
        # Create validator
        validate_max_100 = validate_max(100)

        # Use validator
        validate_max_100(50)  # OK
        validate_max_100(101)  # Raises ValidationError
        ```
    """
    max_value = float(max_value)
    return create_validator(
        lambda x: isinstance(x, (int, float, Decimal)) and float(x) <= max_value,
        message or f"Value must be at most {max_value}",
    )


def validate_positive(message: Optional[str] = None) -> ValidatorFunc:
    """Create positive number validator.

    Args:
        message: Custom error message

    Returns:
        Validator function that checks if value is positive

    Examples:
        ```python
        # Create validator
        validate_pos = validate_positive()

        # Use validator
        validate_pos(5)  # OK
        validate_pos(0)  # Raises ValidationError
        validate_pos(-1)  # Raises ValidationError
        ```
    """
    return create_validator(
        lambda x: isinstance(x, (int, float, Decimal)) and float(x) > 0,
        message or "Value must be positive",
    )


def validate_negative(message: Optional[str] = None) -> ValidatorFunc:
    """Create negative number validator.

    Args:
        message: Custom error message

    Returns:
        Validator function that checks if value is negative

    Examples:
        ```python
        # Create validator
        validate_neg = validate_negative()

        # Use validator
        validate_neg(-5)  # OK
        validate_neg(0)  # Raises ValidationError
        validate_neg(1)  # Raises ValidationError
        ```
    """
    return create_validator(
        lambda x: isinstance(x, (int, float, Decimal)) and float(x) < 0,
        message or "Value must be negative",
    )


def validate_zero(message: Optional[str] = None) -> ValidatorFunc:
    """Create zero validator.

    Args:
        message: Custom error message

    Returns:
        Validator function that checks if value is zero

    Examples:
        ```python
        # Create validator
        validate_is_zero = validate_zero()

        # Use validator
        validate_is_zero(0)  # OK
        validate_is_zero(1)  # Raises ValidationError
        ```
    """
    return create_validator(
        lambda x: isinstance(x, (int, float, Decimal)) and float(x) == 0,
        message or "Value must be zero",
    )


def validate_range(
    min_value: Optional[Number] = None,
    max_value: Optional[Number] = None,
    message: Optional[str] = None,
) -> ValidatorFunc:
    """Create range validator.

    Args:
        min_value: Minimum value allowed
        max_value: Maximum value allowed
        message: Custom error message

    Returns:
        Validator function that checks if value is within range

    Examples:
        ```python
        # Create validator
        validate_0_100 = validate_range(0, 100)

        # Use validator
        validate_0_100(50)  # OK
        validate_0_100(-1)  # Raises ValidationError
        validate_0_100(101)  # Raises ValidationError
        ```
    """
    return RangeValidator(min_value, max_value, message)
