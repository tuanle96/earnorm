"""Boolean field implementation.

This module provides boolean field types for handling true/false values.
It supports:
- Type validation
- String conversion ('true'/'false', '1'/'0', 'yes'/'no')
- Case insensitive string matching
- Default values
- Database type mapping
- Boolean comparison operations

Examples:
    >>> class User(Model):
    ...     is_active = BooleanField(default=True)
    ...     is_admin = BooleanField(default=False)
    ...     has_verified_email = BooleanField()
    ...
    ...     # Query examples
    ...     admins = User.find(User.is_admin.is_true())
    ...     inactive = User.find(User.is_active.is_false())
    ...     unverified = User.find(User.has_verified_email.negate())
"""

from typing import Any, Final, Optional, Set, Union

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin
from earnorm.fields.validators.base import TypeValidator, Validator

# Constants
TRUE_VALUES: Final[Set[str]] = {"true", "1", "yes", "on", "t", "y"}
FALSE_VALUES: Final[Set[str]] = {"false", "0", "no", "off", "f", "n"}


class BooleanField(BaseField[bool], FieldComparisonMixin):
    """Field for boolean values.

    This field type handles true/false values, with support for:
    - Type validation
    - String conversion ('true'/'false', '1'/'0', 'yes'/'no')
    - Case insensitive string matching
    - Default values
    - Database type mapping
    - Boolean comparison operations

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

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare boolean value for comparison.

        Converts value to boolean using the same rules as convert().

        Args:
            value: Value to prepare

        Returns:
            Prepared boolean value
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                return value
            elif isinstance(value, int):
                return bool(value)
            elif isinstance(value, str):
                value = value.lower().strip()
                if value in self.true_values:
                    return True
                if value in self.false_values:
                    return False
            return None
        except (TypeError, ValueError):
            return None

    def is_true(self) -> ComparisonOperator:
        """Check if value is True.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "equals", True)

    def is_false(self) -> ComparisonOperator:
        """Check if value is False.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "equals", False)

    def equals(self, value: Union[bool, int, str]) -> ComparisonOperator:
        """Check if value equals another value.

        Args:
            value: Value to compare with (will be converted to boolean)

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        prepared_value = self._prepare_value(value)
        if prepared_value is None:
            raise ValueError(
                f"Cannot convert {value} to boolean. "
                f"Valid true values: {sorted(self.true_values)}, "
                f"valid false values: {sorted(self.false_values)}"
            )
        return ComparisonOperator(self.name, "equals", prepared_value)

    def negate(self) -> ComparisonOperator:
        """Get the opposite of the current value.

        Returns:
            ComparisonOperator: Comparison operator with field name and operation
        """
        return ComparisonOperator(self.name, "negate", None)

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
