"""Field validators for EarnORM."""

from typing import Any, Callable, TypeVar

from earnorm.validators.base import (
    BaseValidator,
    ValidationError,
    validate_email,
    validate_length,
    validate_range,
    validate_regex,
)

T = TypeVar("T")
ValidatorFunc = Callable[[Any], None]

__all__ = [
    "BaseValidator",
    "ValidationError",
    "validate_email",
    "validate_length",
    "validate_range",
    "validate_regex",
]
