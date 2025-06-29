"""Number field implementation.

This module provides number field types for handling numeric values.
It supports:
- Integer and float values
- Range validation (min/max)
- Step validation (multiples)
- Unit conversion
- Rounding options
- String parsing

Examples:
    >>> class Product(Model):
    ...     price = FloatField(min_value=0, precision=2)
    ...     quantity = IntegerField(min_value=0)
    ...     rating = FloatField(min_value=1, max_value=5)
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Final, Generic, TypeVar

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import RangeValidator, TypeValidator, Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Type variables
N = TypeVar("N", int, float, Decimal)  # Numeric type

# Constants
DEFAULT_MIN_VALUE: Final[int | float | Decimal | None] = None
DEFAULT_MAX_VALUE: Final[int | float | Decimal | None] = None
DEFAULT_STEP: Final[int | float | Decimal | None] = None
DEFAULT_UNIT: Final[str | None] = None
DEFAULT_PRECISION: Final[int | None] = None
DEFAULT_MAX_DIGITS: Final[int | None] = None
DEFAULT_DECIMAL_PLACES: Final[int | None] = None


class NumberField(Generic[N], BaseField[N], FieldComparisonMixin):
    """Base field for numeric values.

    This field type handles numeric values, with support for:
    - Integer and float values
    - Range validation (min/max)
    - Step validation (multiples)
    - Unit conversion
    - Rounding options
    - String parsing

    Attributes:
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        step: Required step between values
        unit: Unit for display/conversion
        backend_options: Database backend options
    """

    min_value: N | None
    max_value: N | None
    step: N | None
    unit: str | None
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        min_value: N | None = None,
        max_value: N | None = None,
        step: N | None = None,
        unit: str | None = None,
        **options: Any,
    ) -> None:
        """Initialize number field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Required step between values
            unit: Unit for display/conversion
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        # Create validators
        field_validators: list[Validator[Any]] = []
        if min_value is not None or max_value is not None:
            field_validators.append(
                RangeValidator(
                    min_value=min_value,
                    max_value=max_value,
                    message=(f"Value must be between {min_value or '-∞'} " f"and {max_value or '∞'}"),
                )
            )

        options_without_validators = {k: v for k, v in options.items() if k != "validators"}
        super().__init__(validators=field_validators, **options_without_validators)

        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.unit = unit

        # Initialize backend options
        self.backend_options = {}

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare numeric value for comparison.

        Converts value to the appropriate numeric type and validates it.

        Args:
            value: Value to prepare

        Returns:
            DatabaseValue: Prepared numeric value
        """
        if value is None:
            return None

        try:
            # Convert to appropriate numeric type
            if isinstance(self, IntegerField):
                return int(float(str(value)))
            elif isinstance(self, FloatField):
                return float(str(value))
            elif isinstance(self, DecimalField):
                return str(Decimal(str(value)))
            return value  # type: ignore
        except (TypeError, ValueError, InvalidOperation):
            return value  # type: ignore

    def mod(self, divisor: N) -> ComparisonOperator:
        """Check if value is divisible by divisor.

        Args:
            divisor: Value to divide by

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "mod", divisor)

    def round_to(self, precision: int) -> ComparisonOperator:
        """Check if value rounds to a specific precision.

        Args:
            precision: Number of decimal places

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "round_to", precision)

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

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> Any:
        """Validate numeric value.

        This method validates:
        - Value is numeric type
        - Value is within min/max range
        - Value is a multiple of step if specified

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
            if not isinstance(value, (int, float, Decimal)):
                raise FieldValidationError(
                    message=f"Value must be a number, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.step is not None:
                # Handle step validation based on type
                if isinstance(value, Decimal) or isinstance(self.step, Decimal):
                    # Convert both to Decimal for precise division
                    try:
                        step_dec = Decimal(str(self.step))
                        value_dec = Decimal(str(value))
                        remainder = value_dec % step_dec
                        is_multiple = abs(remainder) < Decimal("0.000001")
                    except InvalidOperation:
                        is_multiple = False
                else:
                    # Handle float and int
                    remainder = float(value) % float(self.step)
                    is_multiple = abs(remainder) < 1e-6

                if not is_multiple:
                    raise FieldValidationError(
                        message=f"Value must be a multiple of {self.step}",
                        field_name=self.name,
                        code="invalid_step",
                    )

        return value


class IntegerField(NumberField[int]):
    """Field for integer values.

    This field type handles integer values, with support for:
    - Range validation (min/max)
    - Step validation (multiples)
    - Unit conversion
    - String parsing
    """

    def __init__(
        self,
        *,
        min_value: int | None = DEFAULT_MIN_VALUE,  # type: ignore
        max_value: int | None = DEFAULT_MAX_VALUE,  # type: ignore
        step: int | None = DEFAULT_STEP,  # type: ignore
        unit: str | None = DEFAULT_UNIT,
        **options: Any,
    ) -> None:
        """Initialize integer field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Required step between values
            unit: Unit for display/conversion
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        field_validators: list[Validator[Any]] = [TypeValidator(int)]
        options_without_validators = {k: v for k, v in options.items() if k != "validators"}
        super().__init__(
            min_value=min_value,
            max_value=max_value,
            step=step,
            unit=unit,
            validators=field_validators,
            **options_without_validators,
        )

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "int"},
            "postgres": {"type": "INTEGER"},
            "mysql": {"type": "INT"},
        }

    # async def __get__(
    #     self, instance: Any, owner: Optional[Type[Any]] = None
    # ) -> Union["IntegerField", Optional[int]]:
    #     """Get field value from instance.

    #     This implements the descriptor protocol for attribute access.
    #     The process is:
    #     1. Return field instance if accessed on class
    #     2. Check environment cache first
    #     3. Load from database if not in cache
    #     4. Update cache with loaded value
    #     5. Return value

    #     Args:
    #         instance: Model instance
    #         owner: Model class

    #     Returns:
    #         Union[IntegerField, Optional[int]]: Field instance or value
    #     """
    #     if instance is None:
    #         return self
    #     return await self.convert(
    #         instance.env.get_field_value(instance._name, instance.id, self.name)
    #     )

    async def convert(self, value: Any) -> int | None:
        """_Convert value to integer.

        Handles:
        - None values
        - Integer values
        - Float values (rounds down)
        - String values (parses as integer)

        Args:
            value: Value to convert

        Returns:
            Optional[int]: Converted integer value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to integer")
            if isinstance(value, float):
                value = int(value)
            if isinstance(value, str):
                value = int(float(value))
            return int(value)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to integer: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: int | None, backend: str) -> DatabaseValue:
        """Convert integer to database format.

        Args:
            value: Integer value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Converted integer value or None
        """
        return value

    async def from_db(self, value: DatabaseValue, backend: str) -> int | None:
        """Convert database value to integer.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Optional[int]: Converted integer value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to integer")
            if isinstance(value, (dict, list)):
                raise TypeError("Cannot convert complex types to integer")
            return int(float(str(value)))
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to integer: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e


class FloatField(NumberField[float]):
    """Field for float values.

    This field type handles float values, with support for:
    - Range validation (min/max)
    - Step validation (multiples)
    - Precision control
    - Unit conversion
    - String parsing
    """

    def __init__(
        self,
        *,
        min_value: float | None = DEFAULT_MIN_VALUE,  # type: ignore
        max_value: float | None = DEFAULT_MAX_VALUE,  # type: ignore
        step: float | None = DEFAULT_STEP,  # type: ignore
        precision: int | None = DEFAULT_PRECISION,
        unit: str | None = DEFAULT_UNIT,
        **options: Any,
    ) -> None:
        """Initialize float field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Required step between values
            precision: Number of decimal places
            unit: Unit for display/conversion
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        field_validators: list[Validator[Any]] = [TypeValidator(float)]
        options_without_validators = {k: v for k, v in options.items() if k != "validators"}
        super().__init__(
            min_value=min_value,
            max_value=max_value,
            step=step,
            unit=unit,
            validators=field_validators,
            **options_without_validators,
        )

        self.precision = precision

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "double"},
            "postgres": {"type": "DOUBLE PRECISION"},
            "mysql": {"type": "DOUBLE"},
        }

    async def convert(self, value: Any) -> float | None:
        """Convert value to float.

        Handles:
        - None values
        - Float values
        - Integer values
        - String values (parses as float)
        - Decimal values

        Args:
            value: Value to convert

        Returns:
            Optional[float]: Converted float value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to float")
            if isinstance(value, Decimal):
                value = float(value)
            if isinstance(value, str):
                value = float(value)
            value = float(value)
            if self.precision is not None:
                value = round(value, self.precision)
            return value
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to float: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: float | None, backend: str) -> DatabaseValue:
        """Convert float to database format.

        Args:
            value: Float value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Converted float value or None
        """
        if value is None:
            return None

        if self.precision is not None:
            value = round(value, self.precision)

        return value

    async def from_db(self, value: DatabaseValue, backend: str) -> float | None:
        """Convert database value to float.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Optional[float]: Converted float value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to float")
            if isinstance(value, (dict, list)):
                raise TypeError("Cannot convert complex types to float")
            value = float(str(value))
            if self.precision is not None:
                value = round(value, self.precision)
            return value
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to float: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e


class DecimalField(NumberField[Decimal]):
    """Field for decimal values.

    This field type handles decimal values, with support for:
    - Range validation (min/max)
    - Step validation (multiples)
    - Precision control
    - Unit conversion
    - String parsing
    """

    def __init__(
        self,
        *,
        min_value: Decimal | int | float | str | None = DEFAULT_MIN_VALUE,
        max_value: Decimal | int | float | str | None = DEFAULT_MAX_VALUE,
        step: Decimal | int | float | str | None = DEFAULT_STEP,
        max_digits: int | None = DEFAULT_MAX_DIGITS,
        decimal_places: int | None = DEFAULT_DECIMAL_PLACES,
        unit: str | None = DEFAULT_UNIT,
        **options: Any,
    ) -> None:
        """Initialize decimal field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Required step between values
            max_digits: Maximum total digits
            decimal_places: Maximum decimal places
            unit: Unit for display/conversion
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
            InvalidOperation: If decimal conversion fails
        """
        # Convert min/max/step to Decimal
        min_value_dec = Decimal(str(min_value)) if min_value is not None else None
        max_value_dec = Decimal(str(max_value)) if max_value is not None else None
        step_dec = Decimal(str(step)) if step is not None else None

        field_validators: list[Validator[Any]] = [TypeValidator(Decimal)]
        options_without_validators = {k: v for k, v in options.items() if k != "validators"}
        super().__init__(
            min_value=min_value_dec,
            max_value=max_value_dec,
            step=step_dec,
            unit=unit,
            validators=field_validators,
            **options_without_validators,
        )

        self.max_digits = max_digits
        self.decimal_places = decimal_places

        # Initialize backend options
        self.backend_options = {
            "mongodb": {
                "type": "decimal",
                "maxDigits": max_digits,
                "decimalPlaces": decimal_places,
            },
            "postgres": {
                "type": "NUMERIC",
                "precision": max_digits,
                "scale": decimal_places,
            },
            "mysql": {
                "type": "DECIMAL",
                "precision": max_digits,
                "scale": decimal_places,
            },
        }

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> None:
        """Validate decimal value.

        This method validates:
        - Value is Decimal type
        - Value is within min/max range
        - Value is a multiple of step if specified
        - Value fits within max_digits/decimal_places

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value, context)

        if value is not None:
            if not isinstance(value, Decimal):
                raise FieldValidationError(
                    message=f"Value must be a Decimal, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.max_digits is not None or self.decimal_places is not None:
                str_value = str(value.normalize())
                if "." in str_value:
                    integer_part, decimal_part = str_value.split(".")
                else:
                    integer_part, decimal_part = str_value, ""

                if self.max_digits is not None:
                    total_digits = len(integer_part.lstrip("-")) + len(decimal_part)
                    if total_digits > self.max_digits:
                        raise FieldValidationError(
                            message=(f"Value has {total_digits} digits, " f"but only {self.max_digits} allowed"),
                            field_name=self.name,
                            code="max_digits",
                        )

                if self.decimal_places is not None:
                    if len(decimal_part) > self.decimal_places:
                        raise FieldValidationError(
                            message=(
                                f"Value has {len(decimal_part)} decimal places, "
                                f"but only {self.decimal_places} allowed"
                            ),
                            field_name=self.name,
                            code="decimal_places",
                        )

    async def convert(self, value: Any) -> Decimal | None:
        """Convert value to decimal.

        Handles:
        - None values
        - Decimal values
        - Integer values
        - Float values
        - String values (parses as decimal)

        Args:
            value: Value to convert

        Returns:
            Optional[Decimal]: Converted decimal value or None

        Raises:
            FieldValidationError: If value cannot be converted
            InvalidOperation: If decimal conversion fails
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to decimal")
            if isinstance(value, (int, float)):
                value = str(value)
            return Decimal(value)
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to decimal: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Decimal | None, backend: str) -> DatabaseValue:
        """Convert decimal to database format.

        Args:
            value: Decimal value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Converted decimal value or None

        Raises:
            InvalidOperation: If decimal conversion fails
        """
        if value is None:
            return None

        if self.decimal_places is not None:
            value = value.quantize(Decimal(f"0.{'0' * self.decimal_places}"))

        return str(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Decimal | None:
        """Convert database value to decimal.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Optional[Decimal]: Converted decimal value or None

        Raises:
            FieldValidationError: If value cannot be converted
            InvalidOperation: If decimal conversion fails
        """
        if value is None:
            return None

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to decimal")
            if isinstance(value, (dict, list)):
                raise TypeError("Cannot convert complex types to decimal")
            decimal_value = Decimal(str(value))
            if self.decimal_places is not None:
                decimal_value = decimal_value.quantize(Decimal(f"0.{'0' * self.decimal_places}"))
            return decimal_value
        except (TypeError, ValueError, InvalidOperation) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to decimal: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e


class PositiveIntegerField(IntegerField):
    """Field for positive integer values."""

    def __init__(self, *, min_value: int | None = 0, **options: Any) -> None:
        """Initialize positive integer field.

        Args:
            min_value: Minimum allowed value (default: 0)
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        super().__init__(min_value=min_value, **options)


class NegativeIntegerField(IntegerField):
    """Field for negative integer values."""

    def __init__(self, *, max_value: int | None = 0, **options: Any) -> None:
        """Initialize negative integer field.

        Args:
            max_value: Maximum allowed value (default: 0)
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        super().__init__(max_value=max_value, **options)


class AutoIncrementField(IntegerField):
    """Field for auto-incrementing integer values."""

    def __init__(self, *, primary_key: bool = True, **options: Any) -> None:
        """Initialize auto-increment field.

        Args:
            primary_key: Whether this field is the primary key
            **options: Additional field options

        Raises:
            FieldValidationError: If validation fails
        """
        options["required"] = False
        super().__init__(**options)
