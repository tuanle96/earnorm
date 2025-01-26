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
    ...         super().__init__()
    ...         self.min_length = min_length
    ...
    ...     async def validate(self, value: str, context: ValidationContext) -> None:
    ...         if len(value) < self.min_length:
    ...             raise FieldValidationError(
    ...                 message=f"Value must be at least {self.min_length} characters long",
    ...                 field_name=context.field.name
    ...             )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import (
    Any,
    Dict,
    Final,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    final,
)

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField

# Type variables with constraints
T_contra = TypeVar("T_contra", contravariant=True)
T = TypeVar("T", bound=Any)

# Type aliases with better type hints
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidationMetadata = Dict[str, Any]


@dataclass(frozen=True)
class ValidationContext:
    """Context for validation.

    This class provides context information for validation, including:
    - The field being validated
    - The value being validated
    - Additional metadata for validation

    Attributes:
        field: Field being validated
        value: Value being validated
        metadata: Additional validation metadata
    """

    field: BaseField[Any]
    value: Any
    metadata: ValidationMetadata = dataclass_field(default_factory=dict)


class ValidatorProtocol(Protocol[T_contra]):
    """Protocol for validator interface.

    This protocol defines the interface that all validators must implement.
    """

    async def validate(self, value: T_contra, context: ValidationContext) -> None:
        """Validate value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If validation fails
        """
        pass


class Validator(Generic[T], ValidatorProtocol[T], ABC):
    """Base validator class.

    This class provides the base implementation for all validators.
    It supports:
    - Custom error messages
    - Error codes for identifying error types
    - Async validation
    - Validation context

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
        self.message: Optional[str] = message
        self.code: Optional[str] = code

    @abstractmethod
    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If validation fails
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement validate()")

    async def __call__(self, value: T, context: ValidationContext) -> None:
        """Call validator.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If validation fails
        """
        await self.validate(value, context)


@final
class ValidatorChain(Validator[T]):
    """Chain of validators.

    This class allows combining multiple validators into a single validator.
    Validators are applied in sequence, and validation stops at first failure.

    Attributes:
        validators: List of validators to apply in sequence
    """

    def __init__(self, validators: Sequence[Validator[T]]) -> None:
        """Initialize validator chain.

        Args:
            validators: Sequence of validators to apply
        """
        super().__init__()
        self.validators: List[Validator[T]] = list(validators)

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value using all validators in chain.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If any validator fails
        """
        for validator in self.validators:
            await validator.validate(value, context)


@final
class RequiredValidator(Validator[T]):
    """Validator for required fields.

    This validator ensures that a value is not None.
    It is typically used as the first validator in a chain.
    """

    DEFAULT_MESSAGE: Final[str] = "This field is required"
    DEFAULT_CODE: Final[str] = "required"

    def __init__(
        self,
        message: str = DEFAULT_MESSAGE,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize required validator.

        Args:
            message: Error message
            code: Error code
        """
        super().__init__(message=message)
        self.code = code

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value is not None.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is None
        """
        if value is None:
            raise FieldValidationError(
                message=self.message or self.DEFAULT_MESSAGE,
                field_name=getattr(context.field, "name", "unknown"),
            )


@final
class TypeValidator(Validator[T]):
    """Validator for value type.

    This validator ensures that a value is of the correct type.
    It supports:
    - Basic types (str, int, float, bool)
    - Custom types
    - Optional values (None is allowed)
    """

    DEFAULT_CODE: Final[str] = "invalid_type"

    def __init__(
        self,
        value_type: type,
        message: Optional[str] = None,
        code: str = DEFAULT_CODE,
    ) -> None:
        """Initialize type validator.

        Args:
            value_type: Expected value type
            message: Error message template
            code: Error code
        """
        super().__init__(message=message)
        self.code = code
        self.value_type: type = value_type

    async def validate(self, value: T, context: ValidationContext) -> None:
        """Validate value is of correct type.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is of wrong type
        """
        if value is not None and not isinstance(value, self.value_type):
            raise FieldValidationError(
                message=self.message
                or f"Expected {self.value_type.__name__}, got {type(value).__name__}",
                field_name=getattr(context.field, "name", "unknown"),
            )


class RangeValidator(Validator[T]):
    """Validator for value range.

    This validator ensures that a value is within a specified range.
    It supports:
    - Minimum value
    - Maximum value
    - Optional bounds (None means no bound)
    - Any comparable type
    """

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
            FieldValidationError: If value is outside range
        """
        if value is not None:
            if self.min_value is not None and value < self.min_value:  # type: ignore
                raise FieldValidationError(
                    message=self.message
                    or f"Value must be greater than {self.min_value}",
                    field_name=getattr(context.field, "name", "unknown"),
                )
            if self.max_value is not None and value > self.max_value:  # type: ignore
                raise FieldValidationError(
                    message=self.message or f"Value must be less than {self.max_value}",
                    field_name=getattr(context.field, "name", "unknown"),
                )


class RegexValidator(Validator[Optional[str]]):
    """Validator for regex pattern matching.

    This validator ensures that a string value matches a regex pattern.
    It supports:
    - Custom patterns
    - Optional values (None is allowed)
    - Custom error messages
    """

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

    async def validate(self, value: Optional[str], context: ValidationContext) -> None:
        """Validate value matches pattern.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value does not match pattern
        """
        import re

        if value is not None and not re.match(self.pattern, value):
            raise FieldValidationError(
                message=self.message or f"Value must match pattern {self.pattern}",
                field_name=getattr(context.field, "name", "unknown"),
            )
