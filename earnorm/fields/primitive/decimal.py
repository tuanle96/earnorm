"""Decimal field implementation.

This module provides decimal field type for handling decimal numbers.
It supports:
- Decimal validation
- Precision and scale control
- Range validation (min/max)
- Rounding control
- Database type mapping
- Decimal comparison operations

Examples:
    >>> class Product(Model):
    ...     price = DecimalField(max_digits=10, decimal_places=2)
    ...     weight = DecimalField(max_digits=5, decimal_places=3)
    ...     rating = DecimalField(max_digits=3, decimal_places=1, min_value=0, max_value=5)
    ...
    ...     # Query examples
    ...     affordable = Product.find(Product.price.less_than(100))
    ...     heavy = Product.find(Product.weight.greater_than(10))
    ...     top_rated = Product.find(Product.rating.greater_than_or_equal(4.5))
"""

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Any, Final

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import RangeValidator, TypeValidator, Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Constants
DEFAULT_MAX_DIGITS: Final[int] = 65
DEFAULT_DECIMAL_PLACES: Final[int] = 30
DEFAULT_ROUNDING: Final[str] = ROUND_HALF_EVEN


class DecimalField(BaseField[Decimal], FieldComparisonMixin):
    """Field for decimal numbers.

    This field type handles decimal numbers, with support for:
    - Decimal validation
    - Precision and scale control
    - Range validation (min/max)
    - Rounding control
    - Database type mapping
    - Decimal comparison operations

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
    min_value: Decimal | None
    max_value: Decimal | None
    rounding: str
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        max_digits: int = DEFAULT_MAX_DIGITS,
        decimal_places: int = DEFAULT_DECIMAL_PLACES,
        min_value: Decimal | float | str | int | None = None,
        max_value: Decimal | float | str | int | None = None,
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
                    min_value=(Decimal(str(min_value)) if min_value is not None else None),
                    max_value=(Decimal(str(max_value)) if max_value is not None else None),
                    message=(f"Value must be between {min_value or '-∞'} " f"and {max_value or '∞'}"),
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

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> Any:
        """Validate decimal value.

        This method validates:
        - Value is decimal type
        - Value is within min/max range
        - Value precision and scale

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Any: The validated value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

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
                    message=(f"Value has {digits} digits, but only {self.max_digits} " "are allowed"),
                    field_name=self.name,
                    code="max_digits_exceeded",
                )

            if decimals > self.decimal_places:
                raise FieldValidationError(
                    message=(f"Value has {decimals} decimal places, but only " f"{self.decimal_places} are allowed"),
                    field_name=self.name,
                    code="decimal_places_exceeded",
                )

        return value

    async def convert(self, value: Any) -> Decimal | None:
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
                message=f"Cannot convert {value} to decimal: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare decimal value for comparison.

        Converts value to decimal and handles precision/scale.

        Args:
            value: Value to prepare

        Returns:
            Prepared decimal value as string
        """
        if value is None:
            return None

        try:
            if isinstance(value, Decimal):
                decimal_value = value
            elif isinstance(value, (float, str, int)):
                decimal_value = Decimal(str(value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to decimal")

            if self.decimal_places > 0:
                decimal_value = decimal_value.quantize(
                    Decimal(f"0.{'0' * self.decimal_places}"),
                    rounding=self.rounding,
                )

            return str(decimal_value)
        except (TypeError, ValueError, InvalidOperation):
            return None

    def less_than(self, value: Decimal | float | str | int) -> ComparisonOperator:
        """Check if value is less than other value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "lt", self._prepare_value(value))

    def less_than_or_equal(self, value: Decimal | float | str | int) -> ComparisonOperator:
        """Check if value is less than or equal to other value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "lte", self._prepare_value(value))

    def greater_than(self, value: Decimal | float | str | int) -> ComparisonOperator:
        """Check if value is greater than other value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "gt", self._prepare_value(value))

    def greater_than_or_equal(self, value: Decimal | float | str | int) -> ComparisonOperator:
        """Check if value is greater than or equal to other value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "gte", self._prepare_value(value))

    def between(
        self,
        min_value: Decimal | float | str | int,
        max_value: Decimal | float | str | int,
    ) -> ComparisonOperator:
        """Check if value is between min and max values.

        Args:
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name,
            "between",
            [self._prepare_value(min_value), self._prepare_value(max_value)],
        )

    def in_range(
        self,
        min_value: Decimal | float | str | int,
        max_value: Decimal | float | str | int,
    ) -> ComparisonOperator:
        """Alias for between().

        Args:
            min_value: Minimum value
            max_value: Maximum value

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return self.between(min_value, max_value)

    def in_list(self, values: list[Decimal | float | str | int]) -> ComparisonOperator:
        """Check if value is in list of values.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "in", prepared_values)

    def not_in_list(self, values: list[Decimal | float | str | int]) -> ComparisonOperator:
        """Check if value is not in list of values.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "not_in", prepared_values)

    def is_integer(self) -> ComparisonOperator:
        """Check if value is an integer (no decimal places).

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_integer", None)

    def is_positive(self) -> ComparisonOperator:
        """Check if value is positive (> 0).

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_positive", None)

    def is_negative(self) -> ComparisonOperator:
        """Check if value is negative (< 0).

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_negative", None)

    def is_zero(self) -> ComparisonOperator:
        """Check if value is zero.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_zero", None)

    async def to_db(self, value: Decimal | None, backend: str) -> DatabaseValue:
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

        return str(value)  # Convert to string for database storage

    async def from_db(self, value: DatabaseValue, backend: str) -> Decimal | None:
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
                message=f"Cannot convert database value to decimal: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e
