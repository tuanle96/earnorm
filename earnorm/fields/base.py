"""Base field implementation.

This module provides the base field class for all field types.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast

from earnorm.fields.types import ValidatorFunc

T = TypeVar("T")  # Value type


class ValidationError(Exception):
    """Validation error with field name and code.

    Attributes:
        message: Error message
        field_name: Name of field that failed validation
        code: Error code for identifying error type
    """

    def __init__(
        self,
        message: str,
        field_name: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Field name
            code: Error code for identifying error type
        """
        self.message = message
        self.field_name = field_name
        self.code = code or "validation_error"
        super().__init__(f"{field_name}: {message} (code={self.code})")


class Field(Generic[T]):
    """Base field class.

    Attributes:
        name: Field name
        required: Whether field is required
        readonly: Whether field is readonly
        default: Default value
        validators: List of validator functions
        backend_options: Backend-specific options
    """

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        required: bool = False,
        readonly: bool = False,
        default: Optional[T] = None,
        validators: Optional[List[ValidatorFunc]] = None,
        backend_options: Optional[Dict[str, Dict[str, Any]]] = None,
        **options: Any,
    ) -> None:
        """Initialize field.

        Args:
            name: Field name
            required: Whether field is required
            readonly: Whether field is readonly
            default: Default value
            validators: List of validator functions
            backend_options: Backend-specific options
            **options: Additional options
        """
        self.name = name or ""
        self.required = required
        self.readonly = readonly
        self.default = default
        self.validators = validators or []
        self.backend_options = backend_options or {}
        self.options = options
        self._value: Optional[T] = None

    def __get__(self, instance: Any, owner: Any) -> Union["Field[T]", T]:
        """Get field value.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Field value converted to the appropriate type
        """
        if instance is None:
            return self

        # Return None if no value is set
        if self._value is None:
            return None  # type: ignore

        # Each field type should override this method to implement proper conversion
        return self._value  # type: ignore

    def __set__(self, instance: Any, value: Any) -> None:
        """Set field value.

        Args:
            instance: Model instance
            value: Value to set

        Raises:
            ValidationError: If validation fails
        """
        if self.readonly:
            raise ValidationError(
                message="Field is readonly",
                field_name=self.name,
                code="readonly",
            )

        # Store the converted value
        self._value = value

    async def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if self.required:
                raise ValidationError(
                    message="Field is required",
                    field_name=self.name,
                    code="required",
                )
            return

        for validator in self.validators:
            result = await validator(value)
            if isinstance(result, tuple):
                valid, message = result
                if not valid:
                    raise ValidationError(
                        message=message,
                        field_name=self.name,
                        code="validation_failed",
                    )
            elif not result:
                raise ValidationError(
                    message="Validation failed",
                    field_name=self.name,
                    code="validation_failed",
                )

    async def convert(self, value: Any) -> Optional[T]:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        return value

    async def to_db(self, value: Optional[T], backend: str) -> Any:
        """Convert value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Database value
        """
        return value

    async def from_db(self, value: Any, backend: str) -> Optional[T]:
        """Convert database value to field type.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Field value
        """
        return value
