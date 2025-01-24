"""Field validator base implementation.

This module provides the base validator system for field validation.
It supports:
- Synchronous and asynchronous validation
- Validation chaining
- Custom validation rules
- Error handling
- Validation context

Examples:
    >>> class MinLengthValidator(Validator[str]):
    ...     def __init__(self, min_length: int) -> None:
    ...         self.min_length = min_length
    ...
    ...     async def validate(self, value: str, context: ValidationContext) -> None:
    ...         if len(value) < self.min_length:
    ...             raise ValidationError(
    ...                 message=f"Value must be at least {self.min_length} characters long",
    ...                 field_name=context.field.name,
    ...                 code="min_length"
    ...             )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Dict, Generic, Optional, Sequence, TypeVar

from earnorm.fields.base import Field, ValidationError

T = TypeVar("T")  # Type of value to validate


@dataclass
class ValidationContext:
    """Context for validation.

    Attributes:
        field: Field being validated
        value: Value being validated
        metadata: Additional validation metadata
    """

    field: Field[Any]
    value: Any
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)


class Validator(Generic[T], ABC):
    """Base validator class.

    Attributes:
        message: Error message template
        code: Error code for identifying error type
    """

    def __init__(
        self, *, message: Optional[str] = None, code: Optional[str] = None
    ) -> None:
        """Initialize validator.

        Args:
            message: Error message template
            code: Error code for identifying error type
        """
        self.message = message
        self.code = code

    @abstractmethod
    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If validation fails
        """
        pass

    def __call__(self, value: T, context: ValidationContext) -> None:
        """Call validator.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If validation fails
        """
        return self.validate(value, context)  # type: ignore


class ValidatorChain(Validator[T]):
    """Chain of validators.

    Attributes:
        validators: List of validators to apply in sequence
    """

    def __init__(self, validators: Sequence[Validator[T]]) -> None:
        """Initialize validator chain.

        Args:
            validators: Sequence of validators to apply
        """
        super().__init__()
        self.validators = list(validators)

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value using all validators in chain.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If any validator fails
        """
        for validator in self.validators:
            await validator.validate(value, context)


class RequiredValidator(Validator[T]):
    """Validator for required fields."""

    def __init__(
        self,
        message: str = "This field is required",
        code: str = "required",
    ) -> None:
        """Initialize required validator.

        Args:
            message: Error message
            code: Error code
        """
        super().__init__(message=message, code=code)

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value is not None.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is None
        """
        if value is None:
            raise ValidationError(
                message=self.message or "This field is required",
                field_name=context.field.name,
                code=self.code or "required",
            )


class TypeValidator(Validator[T]):
    """Validator for value type."""

    def __init__(
        self,
        value_type: type,
        message: Optional[str] = None,
        code: str = "invalid_type",
    ) -> None:
        """Initialize type validator.

        Args:
            value_type: Expected value type
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.value_type = value_type

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value is of correct type.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is of wrong type
        """
        if value is not None and not isinstance(value, self.value_type):
            raise ValidationError(
                message=self.message
                or f"Expected {self.value_type.__name__}, got {type(value).__name__}",
                field_name=context.field.name,
                code=self.code or "invalid_type",
            )


class RangeValidator(Validator[T]):
    """Validator for value range."""

    def __init__(
        self,
        min_value: Optional[T] = None,
        max_value: Optional[T] = None,
        message: Optional[str] = None,
        code: str = "invalid_range",
    ) -> None:
        """Initialize range validator.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.min_value = min_value
        self.max_value = max_value

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value is within range.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value is outside range
        """
        if value is not None:
            if self.min_value is not None and value < self.min_value:  # type: ignore
                raise ValidationError(
                    message=self.message
                    or f"Value must be greater than {self.min_value}",
                    field_name=context.field.name,
                    code=self.code or "invalid_range",
                )
            if self.max_value is not None and value > self.max_value:  # type: ignore
                raise ValidationError(
                    message=self.message or f"Value must be less than {self.max_value}",
                    field_name=context.field.name,
                    code=self.code or "invalid_range",
                )


class RegexValidator(Validator[str]):
    """Validator for regex pattern matching."""

    def __init__(
        self,
        pattern: str,
        message: Optional[str] = None,
        code: str = "invalid_format",
    ) -> None:
        """Initialize regex validator.

        Args:
            pattern: Regex pattern to match
            message: Error message template
            code: Error code
        """
        super().__init__(message=message, code=code)
        self.pattern = pattern

    async def validate(self, value: str, context: ValidationContext) -> None:
        """Validate value matches pattern.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If value doesn't match pattern
        """
        import re

        if not re.match(self.pattern, value):
            raise ValidationError(
                message=self.message or f"Value must match pattern {self.pattern}",
                field_name=context.field.name,
                code=self.code or "invalid_format",
            )
