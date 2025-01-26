"""Boolean field implementation.

This module provides boolean field types for handling true/false values.
It supports:
- Type validation
- String conversion ('true'/'false', '1'/'0', 'yes'/'no')
- Case insensitive string matching
- Default values
- Database type mapping

Examples:
    >>> class User(Model):
    ...     is_active = BooleanField(default=True)
    ...     is_admin = BooleanField(default=False)
    ...     has_verified_email = BooleanField()
"""

from typing import Any, Final, Optional, Set

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import TypeValidator, Validator

# Constants
TRUE_VALUES: Final[Set[str]] = {"true", "1", "yes", "on", "t", "y"}
FALSE_VALUES: Final[Set[str]] = {"false", "0", "no", "off", "f", "n"}


class BooleanField(BaseField[bool]):
    """Field for boolean values.

    This field type handles true/false values, with support for:
    - Type validation
    - String conversion ('true'/'false', '1'/'0', 'yes'/'no')
    - Case insensitive string matching
    - Default values
    - Database type mapping

    Attributes:
        true_values: Set of string values that convert to True
        false_values: Set of string values that convert to False
        backend_options: Database backend options
    """

    true_values: Set[str]
    false_values: Set[str]
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        true_values: Optional[Set[str]] = None,
        false_values: Optional[Set[str]] = None,
        **options: Any,
    ) -> None:
        """Initialize boolean field.

        Args:
            true_values: Custom set of string values that convert to True
            false_values: Custom set of string values that convert to False
            **options: Additional field options
        """
        field_validators: list[Validator[Any]] = [TypeValidator(bool)]
        super().__init__(validators=field_validators, **options)

        self.true_values = true_values or TRUE_VALUES
        self.false_values = false_values or FALSE_VALUES

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "bool"},
            "postgres": {"type": "BOOLEAN"},
            "mysql": {"type": "BOOLEAN"},
        }

    async def validate(self, value: Any) -> None:
        """Validate boolean value.

        This method validates:
        - Value is boolean type
        - Required/optional

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None and not isinstance(value, bool):
            raise FieldValidationError(
                message=f"Value must be a boolean, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

    async def convert(self, value: Any) -> Optional[bool]:
        """Convert value to boolean.

        Handles:
        - None values
        - Boolean values
        - Integer values (0=False, non-zero=True)
        - String values (case insensitive):
          - True: 'true', '1', 'yes', 'on', 't', 'y'
          - False: 'false', '0', 'no', 'off', 'f', 'n'

        Args:
            value: Value to convert

        Returns:
            Converted boolean value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return bool(value)

        if isinstance(value, str):
            value = value.lower().strip()
            if value in self.true_values:
                return True
            if value in self.false_values:
                return False

        raise FieldValidationError(
            message=(
                f"Cannot convert {type(value).__name__} to boolean. "
                f"Valid true values: {sorted(self.true_values)}, "
                f"valid false values: {sorted(self.false_values)}"
            ),
            field_name=self.name,
            code="conversion_error",
        )

    async def to_db(self, value: Optional[bool], backend: str) -> DatabaseValue:
        """Convert boolean to database format.

        Args:
            value: Boolean value to convert
            backend: Database backend type

        Returns:
            Converted boolean value or None
        """
        return value

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[bool]:
        """Convert database value to boolean.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted boolean value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            return bool(value)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to boolean: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
