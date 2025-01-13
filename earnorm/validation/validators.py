"""Base validators for EarnORM."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union


class ValidationError(Exception):
    """Validation error."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Initialize validation error."""
        super().__init__(message)
        self.message = message
        self.field = field


class Validator(ABC):
    """Base validator."""

    @abstractmethod
    def __call__(self, value: Any) -> None:
        """Validate value."""
        pass


class AsyncValidator(ABC):
    """Base async validator."""

    @abstractmethod
    async def __call__(self, value: Any) -> None:
        """Validate value asynchronously."""
        pass


class FieldValidator(Validator):
    """Field validator."""

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize field validator."""
        self.message = message


class ModelValidator(Validator):
    """Model validator."""

    def __init__(self, fields: Optional[List[str]] = None) -> None:
        """Initialize model validator."""
        self.fields = fields or []


# Built-in validators
class RequiredValidator(FieldValidator):
    """Required field validator."""

    def __call__(self, value: Any) -> None:
        """Validate value is not None."""
        if value is None:
            raise ValidationError(self.message or "Field is required")


class MinLengthValidator(FieldValidator):
    """Minimum length validator."""

    def __init__(self, min_length: int, message: Optional[str] = None) -> None:
        """Initialize minimum length validator."""
        super().__init__(message)
        self.min_length = min_length

    def __call__(self, value: Any) -> None:
        """Validate minimum length."""
        if value is not None and len(value) < self.min_length:
            raise ValidationError(
                self.message or f"Length must be at least {self.min_length}"
            )


class MaxLengthValidator(FieldValidator):
    """Maximum length validator."""

    def __init__(self, max_length: int, message: Optional[str] = None) -> None:
        """Initialize maximum length validator."""
        super().__init__(message)
        self.max_length = max_length

    def __call__(self, value: Any) -> None:
        """Validate maximum length."""
        if value is not None and len(value) > self.max_length:
            raise ValidationError(
                self.message or f"Length must be at most {self.max_length}"
            )


class MinValueValidator(FieldValidator):
    """Minimum value validator."""

    def __init__(
        self, min_value: Union[int, float], message: Optional[str] = None
    ) -> None:
        """Initialize minimum value validator."""
        super().__init__(message)
        self.min_value = min_value

    def __call__(self, value: Any) -> None:
        """Validate minimum value."""
        if value is not None and value < self.min_value:
            raise ValidationError(
                self.message or f"Value must be at least {self.min_value}"
            )


class MaxValueValidator(FieldValidator):
    """Maximum value validator."""

    def __init__(
        self, max_value: Union[int, float], message: Optional[str] = None
    ) -> None:
        """Initialize maximum value validator."""
        super().__init__(message)
        self.max_value = max_value

    def __call__(self, value: Any) -> None:
        """Validate maximum value."""
        if value is not None and value > self.max_value:
            raise ValidationError(
                self.message or f"Value must be at most {self.max_value}"
            )


class RegexValidator(FieldValidator):
    """Regex validator."""

    def __init__(self, pattern: str, message: Optional[str] = None) -> None:
        """Initialize regex validator."""
        super().__init__(message)
        self.pattern = pattern

    def __call__(self, value: Any) -> None:
        """Validate regex pattern."""
        import re

        if value is not None and not re.match(self.pattern, str(value)):
            raise ValidationError(
                self.message or f"Value does not match pattern {self.pattern}"
            )
