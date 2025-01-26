"""Decimal field implementation.

This module provides decimal field type for handling decimal numbers.
It supports:
- Decimal validation
- Precision and scale control
- Range validation (min/max)
- Rounding control
- Database type mapping

Examples:
    >>> class Product(Model):
    ...     price = DecimalField(max_digits=10, decimal_places=2)
    ...     weight = DecimalField(max_digits=5, decimal_places=3)
    ...     rating = DecimalField(max_digits=3, decimal_places=1, min_value=0, max_value=5)
"""

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Final, Optional, Union

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import RangeValidator, TypeValidator, Validator

# Constants
DEFAULT_MAX_DIGITS: Final[int] = 65
DEFAULT_DECIMAL_PLACES: Final[int] = 30
DEFAULT_ROUNDING: Final[str] = ROUND_HALF_EVEN


class DecimalField(BaseField[Decimal]):
    """Field for decimal numbers.

    This field type handles decimal numbers, with support for:
    - Decimal validation
    - Precision and scale control
    - Range validation (min/max)
    - Rounding control
    - Database type mapping

    Attributes:
        max_digits: Maximum number of digits (precision)
        decimal_places: Number of decimal places (scale)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        rounding: Rounding mode for decimal operations
        backend_options: Database backend options
    """

    max_digits: int
    decimal_places: int
    min_value: Optional[Decimal]
    max_value: Optional[Decimal]
    rounding: str
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        max_digits: int = DEFAULT_MAX_DIGITS,
        decimal_places: int = DEFAULT_DECIMAL_PLACES,
        min_value: Optional[Union[Decimal, float, str, int]] = None,
        max_value: Optional[Union[Decimal, float, str, int]] = None,
        rounding: str = DEFAULT_ROUNDING,
        **options: Any,
    ) -> None:
        """Initialize decimal field.

        Args:
            max_digits: Maximum number of digits (precision)
            decimal_places: Number of decimal places (scale)
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            rounding: Rounding mode for decimal operations
            **options: Additional field options

        Raises:
            ValueError: If max_digits or decimal_places are invalid
        """
        if max_digits < 1:
            raise ValueError("max_digits must be positive")
            if decimal_places < 0:
                raise ValueError("decimal_places must be non-negative")
        if decimal_places > max_digits:
            raise ValueError("decimal_places cannot be greater than max_digits")

        # Create validators
        field_validators: list[Validator[Any]] = [TypeValidator(Decimal)]
        if min_value is not None or max_value is not None:
            field_validators.append(
                RangeValidator(
                    min_value=(
                        Decimal(str(min_value)) if min_value is not None else None
                    ),
                    max_value=(
                        Decimal(str(max_value)) if max_value is not None else None
                    ),
                    message=(
                        f"Value must be between {min_value or '-∞'} "
                        f"and {max_value or '∞'}"
                    ),
                )
            )

        super().__init__(validators=field_validators, **options)

        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.min_value = Decimal(str(min_value)) if min_value is not None else None
        self.max_value = Decimal(str(max_value)) if max_value is not None else None
        self.rounding = rounding

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "decimal"},
            "postgres": {"type": f"DECIMAL({max_digits}, {decimal_places})"},
            "mysql": {"type": f"DECIMAL({max_digits}, {decimal_places})"},
        }

    async def validate(self, value: Any) -> None:
        """Validate decimal value.

        This method validates:
        - Value is decimal type
        - Value is within min/max range
        - Value precision and scale

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, Decimal):
                raise FieldValidationError(
                    message=f"Value must be a decimal, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            # Check precision and scale
            str_val = str(value.normalize())
            if "E" in str_val:
                raise FieldValidationError(
                    message="Scientific notation is not supported",
                    field_name=self.name,
                    code="invalid_format",
                )

            parts = str_val.split(".")
            if len(parts) == 2:
                digits = len(parts[0].lstrip("-")) + len(parts[1])
                decimals = len(parts[1])
            else:
                digits = len(parts[0].lstrip("-"))
                decimals = 0

            if digits > self.max_digits:
                raise FieldValidationError(
                    message=(
                        f"Value has {digits} digits, but only {self.max_digits} "
                        "are allowed"
                    ),
                    field_name=self.name,
                    code="max_digits_exceeded",
                )

            if decimals > self.decimal_places:
                raise FieldValidationError(
                    message=(
                        f"Value has {decimals} decimal places, but only "
                        f"{self.decimal_places} are allowed"
                    ),
                    field_name=self.name,
                    code="decimal_places_exceeded",
                )

    async def convert(self, value: Any) -> Optional[Decimal]:
        """Convert value to decimal.

        Handles:
        - None values
        - Decimal objects
        - Float values
        - String values
        - Integer values

        Args:
            value: Value to convert

        Returns:
            Converted decimal value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, Decimal):
                return value
            elif isinstance(value, (float, str, int)):
                return Decimal(str(value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to decimal")
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FieldValidationError(
                message=f"Cannot convert {value} to decimal: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[Decimal], backend: str) -> DatabaseValue:
        """Convert decimal to database format.

        Args:
            value: Decimal value to convert
            backend: Database backend type

        Returns:
            Converted decimal value or None
        """
        if value is None:
            return None

        # Round value if needed
        if self.decimal_places > 0:
            value = value.quantize(
                Decimal(f"0.{'0' * self.decimal_places}"),
                rounding=self.rounding,
            )

            return value

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[Decimal]:
        """Convert database value to decimal.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted decimal value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, Decimal):
                return value
            elif isinstance(value, (float, str, int)):
                return Decimal(str(value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to decimal")
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to decimal: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
