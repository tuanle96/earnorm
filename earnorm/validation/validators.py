"""Base validators for EarnORM."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

from ..metrics.prometheus import metrics_manager


class ValidationError(Exception):
    """Validation error."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Initialize validation error."""
        super().__init__(message)
        self.message = message
        self.field = field


class AsyncValidator(ABC):
    """Base async validator."""

    @abstractmethod
    async def __call__(self, value: Any) -> None:
        """Validate value asynchronously."""
        pass

    async def track_validation(
        self,
        model: str,
        field: str,
        value: Any,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track validation result."""
        await metrics_manager.track_validation(
            model=model,
            field=field,
            validator=self.__class__.__name__,
            value=str(value),
            success=success,
            error=error,
        )


class AsyncFieldValidator(AsyncValidator):
    """Async field validator."""

    def __init__(self, message: Optional[str] = None) -> None:
        """Initialize field validator."""
        self.message = message


class AsyncModelValidator(AsyncValidator):
    """Async model validator."""

    def __init__(self, fields: Optional[List[str]] = None) -> None:
        """Initialize model validator."""
        self.fields = fields or []


# Built-in validators
class RequiredValidator(AsyncFieldValidator):
    """Required field validator."""

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate value is not None."""
        try:
            if value is None:
                raise ValidationError(self.message or "Field is required")
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e


class MinLengthValidator(AsyncFieldValidator):
    """Minimum length validator."""

    def __init__(self, min_length: int, message: Optional[str] = None) -> None:
        """Initialize minimum length validator."""
        super().__init__(message)
        self.min_length = min_length

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate minimum length."""
        try:
            if value is not None and len(value) < self.min_length:
                raise ValidationError(
                    self.message or f"Length must be at least {self.min_length}"
                )
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e


class MaxLengthValidator(AsyncFieldValidator):
    """Maximum length validator."""

    def __init__(self, max_length: int, message: Optional[str] = None) -> None:
        """Initialize maximum length validator."""
        super().__init__(message)
        self.max_length = max_length

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate maximum length."""
        try:
            if value is not None and len(value) > self.max_length:
                raise ValidationError(
                    self.message or f"Length must be at most {self.max_length}"
                )
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e


class MinValueValidator(AsyncFieldValidator):
    """Minimum value validator."""

    def __init__(
        self, min_value: Union[int, float], message: Optional[str] = None
    ) -> None:
        """Initialize minimum value validator."""
        super().__init__(message)
        self.min_value = min_value

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate minimum value."""
        try:
            if value is not None and value < self.min_value:
                raise ValidationError(
                    self.message or f"Value must be at least {self.min_value}"
                )
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e


class MaxValueValidator(AsyncFieldValidator):
    """Maximum value validator."""

    def __init__(
        self, max_value: Union[int, float], message: Optional[str] = None
    ) -> None:
        """Initialize maximum value validator."""
        super().__init__(message)
        self.max_value = max_value

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate maximum value."""
        try:
            if value is not None and value > self.max_value:
                raise ValidationError(
                    self.message or f"Value must be at most {self.max_value}"
                )
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e


class RegexValidator(AsyncFieldValidator):
    """Regex validator."""

    def __init__(self, pattern: str, message: Optional[str] = None) -> None:
        """Initialize regex validator."""
        super().__init__(message)
        self.pattern = pattern

    async def __call__(self, value: Any, model: str = "", field: str = "") -> None:
        """Validate regex pattern."""
        import re

        try:
            if value is not None and not re.match(self.pattern, str(value)):
                raise ValidationError(
                    self.message or f"Value does not match pattern {self.pattern}"
                )
            await self.track_validation(model, field, value, True)
        except ValidationError as e:
            await self.track_validation(model, field, value, False, str(e))
            raise e
