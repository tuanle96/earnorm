"""Numeric field implementation.

This module provides numeric field types for handling numbers.
It supports:
- Integer fields with range and step validation
- Float fields with precision handling
- Decimal fields with fixed precision
- Range validation (min/max values)
- Step validation for multiples
- Auto-increment fields for IDs

Examples:
    >>> class Product(Model):
    ...     id = AutoIncrementField()
    ...     price = DecimalField(min_value=0, max_digits=10, decimal_places=2)
    ...     quantity = PositiveIntegerField(min_value=1)
    ...     rating = FloatField(min_value=0, max_value=5)

    >>> product = Product()
    >>> await product.validate()  # Validates all fields
    >>> product.price = -10  # Raises ValidationError(code="min_value")
    >>> product.quantity = 1.5  # Raises ValidationError(code="invalid_type")
    >>> product.rating = 6  # Raises ValidationError(code="max_value")
"""

import math
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, TypeVar, Union

from earnorm.fields.base import Field, ValidationError

N = TypeVar("N", int, float, Decimal)  # Numeric type


class NumberField(Field[N]):
    """Base field for numeric values.

    This field handles:
    - Type validation for numbers
    - Range validation (min/max)
    - Step validation for multiples
    - Conversion between numeric types

    Attributes:
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        step: Step size for valid values (must be multiple of)

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a number
            - min_value: Value is less than min_value
            - max_value: Value is greater than max_value
            - invalid_step: Value is not a multiple of step
            - conversion_failed: Value cannot be converted to number

    Examples:
        >>> field = NumberField(min_value=0, max_value=100, step=5)
        >>> await field.validate(-1)  # Raises ValidationError(code="min_value")
        >>> await field.validate(101)  # Raises ValidationError(code="max_value")
        >>> await field.validate(7)  # Raises ValidationError(code="invalid_step")
        >>> await field.validate(10)  # Valid
        >>> await field.validate("abc")  # Raises ValidationError(code="invalid_type")
    """

    def __init__(
        self,
        *,
        min_value: Optional[N] = None,
        max_value: Optional[N] = None,
        step: Optional[N] = None,
        **options: Any,
    ) -> None:
        """Initialize number field.

        Args:
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            step: Step size for valid values (must be multiple of)
            **options: Additional field options

        Examples:
            >>> field = NumberField(min_value=0, max_value=100, step=5)
            >>> field = NumberField(min_value=-10)  # Only minimum
            >>> field = NumberField(step=0.5)  # Only step
        """
        super().__init__(**options)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

    async def validate(self, value: Any) -> None:
        """Validate numeric value.

        Validates:
        - Type is numeric
        - Within min/max range
        - Multiple of step

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a number
                - min_value: Value is less than min_value
                - max_value: Value is greater than max_value
                - invalid_step: Value is not a multiple of step

        Examples:
            >>> field = NumberField(min_value=0, max_value=10, step=2)
            >>> await field.validate(-1)  # Raises ValidationError(code="min_value")
            >>> await field.validate(11)  # Raises ValidationError(code="max_value")
            >>> await field.validate(3)  # Raises ValidationError(code="invalid_step")
            >>> await field.validate(4)  # Valid
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (int, float, Decimal)):
                raise ValidationError(
                    message=f"Value must be a number, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.min_value is not None and value < self.min_value:
                raise ValidationError(
                    message=f"Value must be greater than or equal to {self.min_value}, got {value}",
                    field_name=self.name,
                    code="min_value",
                )

            if self.max_value is not None and value > self.max_value:
                raise ValidationError(
                    message=f"Value must be less than or equal to {self.max_value}, got {value}",
                    field_name=self.name,
                    code="max_value",
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
                    raise ValidationError(
                        message=f"Value must be a multiple of {self.step}, got {value}",
                        field_name=self.name,
                        code="invalid_step",
                    )


class IntegerField(NumberField[int]):
    """Field for integer values.

    This field handles:
    - Integer type validation
    - Range validation
    - Step validation
    - Automatic type conversion when accessed

    Examples:
        >>> class Product(Model):
        ...     quantity = IntegerField(min_value=0)
        ...     priority = IntegerField(min_value=1, max_value=5)

        >>> product = Product()
        >>> product.quantity = "10"  # Automatically converts to int
        >>> print(product.quantity)  # 10
        >>> print(type(product.quantity))  # <class 'int'>
    """

    def __init__(
        self,
        *,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        step: Optional[int] = None,
        **options: Any,
    ) -> None:
        """Initialize integer field.

        Args:
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            step: Step size for valid values (must be multiple of)
            **options: Additional field options

        Examples:
            >>> field = IntegerField(min_value=0, max_value=100)
            >>> field = IntegerField(step=2)  # Even numbers only
            >>> field = IntegerField(min_value=1)  # Positive integers
        """
        super().__init__(
            min_value=min_value,
            max_value=max_value,
            step=step,
            **options,
        )

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "int",
                    "min": min_value,
                    "max": max_value,
                },
                "postgres": {
                    "type": "INTEGER",
                },
                "mysql": {
                    "type": "INT",
                },
            }
        )

    def __get__(self, instance: Any, owner: Any) -> Union[int, "IntegerField"]:
        """Get integer value.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            int: The field value converted to integer
            IntegerField: The field instance if accessed on class
        """
        if instance is None:
            return self

        if self._value is None:
            return None  # type: ignore

        # Automatically convert to int when accessed
        return int(self._value)

    async def validate(self, value: Any) -> None:
        """Validate integer value.

        Validates:
        - Type is integer
        - Within min/max range
        - Multiple of step

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not an integer
                - min_value: Value is less than min_value
                - max_value: Value is greater than max_value
                - invalid_step: Value is not a multiple of step

        Examples:
            >>> field = IntegerField(min_value=0, max_value=10, step=2)
            >>> await field.validate(1.5)  # Raises ValidationError(code="invalid_type")
            >>> await field.validate(-1)  # Raises ValidationError(code="min_value")
            >>> await field.validate(11)  # Raises ValidationError(code="max_value")
            >>> await field.validate(3)  # Raises ValidationError(code="invalid_step")
            >>> await field.validate(4)  # Valid
        """
        await super().validate(value)

        if value is not None and not isinstance(value, int):
            raise ValidationError(
                message=f"Value must be an integer, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

    async def convert(self, value: Any) -> Optional[int]:
        """Convert value to integer.

        Handles:
        - None values
        - String to integer conversion
        - Float to integer conversion
        - Decimal to integer conversion

        Args:
            value: Value to convert

        Returns:
            Converted integer value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = IntegerField()
            >>> await field.convert("123")  # Returns 123
            >>> await field.convert(123.5)  # Returns 123
            >>> await field.convert(True)  # Raises ValidationError(code="conversion_failed")
            >>> await field.convert(None)  # Returns None
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to integer")
            if isinstance(value, float) and not value.is_integer():
                raise TypeError("Cannot convert non-integer float to integer")
            return int(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert {type(value).__name__} to integer: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )


class FloatField(NumberField[float]):
    """Field for floating-point values.

    This field handles:
    - Float type validation
    - Range validation
    - Step validation
    - Precision handling

    Examples:
        >>> class Product(Model):
        ...     price = FloatField(min_value=0)
        ...     rating = FloatField(min_value=0, max_value=5)

        >>> product = Product()
        >>> product.price = -1.5  # Raises ValidationError(code="min_value")
        >>> product.rating = 5.5  # Raises ValidationError(code="max_value")
    """

    def __init__(
        self,
        *,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: Optional[float] = None,
        **options: Any,
    ) -> None:
        """Initialize float field.

        Args:
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            step: Step size for valid values (must be multiple of)
            **options: Additional field options

        Examples:
            >>> field = FloatField(min_value=0.0, max_value=1.0)
            >>> field = FloatField(step=0.5)  # Multiples of 0.5
            >>> field = FloatField(min_value=0.0)  # Non-negative floats
        """
        super().__init__(
            min_value=min_value,
            max_value=max_value,
            step=step,
            **options,
        )

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "double",
                    "min": min_value,
                    "max": max_value,
                },
                "postgres": {
                    "type": "DOUBLE PRECISION",
                },
                "mysql": {
                    "type": "DOUBLE",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate float value.

        Validates:
        - Type is float or integer
        - Within min/max range
        - Multiple of step
        - Not NaN or infinite

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a float
                - min_value: Value is less than min_value
                - max_value: Value is greater than max_value
                - invalid_step: Value is not a multiple of step
                - invalid_float: Value is NaN or infinite

        Examples:
            >>> field = FloatField(min_value=0.0, max_value=1.0, step=0.1)
            >>> await field.validate(-0.5)  # Raises ValidationError(code="min_value")
            >>> await field.validate(1.5)  # Raises ValidationError(code="max_value")
            >>> await field.validate(0.15)  # Raises ValidationError(code="invalid_step")
            >>> await field.validate(float('nan'))  # Raises ValidationError(code="invalid_float")
            >>> await field.validate(0.2)  # Valid
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    message=f"Value must be a float, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    raise ValidationError(
                        message="Value cannot be NaN or infinite",
                        field_name=self.name,
                        code="invalid_float",
                    )

    async def convert(self, value: Any) -> Optional[float]:
        """Convert value to float.

        Handles:
        - None values
        - String to float conversion
        - Integer to float conversion
        - Decimal to float conversion

        Args:
            value: Value to convert

        Returns:
            Converted float value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = FloatField()
            >>> await field.convert("123.45")  # Returns 123.45
            >>> await field.convert(123)  # Returns 123.0
            >>> await field.convert(True)  # Raises ValidationError(code="conversion_failed")
            >>> await field.convert(None)  # Returns None
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, bool):
                raise TypeError("Cannot convert boolean to float")
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert {type(value).__name__} to float: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )


class DecimalField(NumberField[Decimal]):
    """Field for decimal values with fixed precision.

    Examples:
        >>> class Product(Model):
        ...     price = DecimalField(
        ...         min_value=0,
        ...         max_digits=10,
        ...         decimal_places=2,
        ...     )
    """

    def __init__(
        self,
        *,
        min_value: Optional[Union[Decimal, int, float, str]] = None,
        max_value: Optional[Union[Decimal, int, float, str]] = None,
        step: Optional[Union[Decimal, int, float, str]] = None,
        max_digits: Optional[int] = None,
        decimal_places: Optional[int] = None,
        **options: Any,
    ) -> None:
        """Initialize decimal field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            step: Step size for valid values
            max_digits: Maximum total digits
            decimal_places: Maximum decimal places
            **options: Additional field options
        """
        # Convert numeric values to Decimal
        min_value_dec = Decimal(str(min_value)) if min_value is not None else None
        max_value_dec = Decimal(str(max_value)) if max_value is not None else None
        step_dec = Decimal(str(step)) if step is not None else None

        super().__init__(
            min_value=min_value_dec,
            max_value=max_value_dec,
            step=step_dec,
            **options,
        )

        self.max_digits = max_digits
        self.decimal_places = decimal_places

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "decimal",
                    "min": min_value,
                    "max": max_value,
                },
                "postgres": {
                    "type": (
                        f"DECIMAL({max_digits}, {decimal_places})"
                        if max_digits is not None and decimal_places is not None
                        else "DECIMAL"
                    ),
                },
                "mysql": {
                    "type": (
                        f"DECIMAL({max_digits}, {decimal_places})"
                        if max_digits is not None and decimal_places is not None
                        else "DECIMAL"
                    ),
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate decimal value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, Decimal):
                try:
                    value = Decimal(str(value))
                except (TypeError, InvalidOperation) as e:
                    raise ValidationError(str(e), self.name)

            if self.max_digits is not None:
                digit_tuple = value.as_tuple()
                digits = len(digit_tuple.digits)
                if digits > self.max_digits:
                    raise ValidationError(
                        f"Value has more than {self.max_digits} digits",
                        self.name,
                    )

            if self.decimal_places is not None:
                # Handle decimal places validation
                digit_tuple = value.as_tuple()
                if digit_tuple.exponent in ("n", "N", "F"):  # NaN or Infinity
                    raise ValidationError(
                        "Value must be a finite number",
                        self.name,
                    )
                # For finite numbers, exponent is always an integer
                # Negative exponent means decimal places
                places = max(0, -int(digit_tuple.exponent))
                if places > self.decimal_places:
                    raise ValidationError(
                        f"Value has more than {self.decimal_places} decimal places",
                        self.name,
                    )

    async def convert(self, value: Any) -> Optional[Decimal]:
        """Convert value to decimal.

        Args:
            value: Value to convert

        Returns:
            Decimal value

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, bool):
                raise ValueError("Boolean values are not allowed")
            return Decimal(str(value))
        except (TypeError, InvalidOperation) as e:
            raise ValidationError(str(e), self.name)


class PositiveIntegerField(IntegerField):
    """Field for positive integer values.

    Examples:
        >>> class Product(Model):
        ...     quantity = PositiveIntegerField(min_value=1)
    """

    def __init__(self, *, min_value: Optional[int] = 0, **options: Any) -> None:
        """Initialize positive integer field.

        Args:
            min_value: Minimum allowed value (must be >= 0)
            **options: Additional field options

        Raises:
            ValueError: If min_value is negative
        """
        if min_value is not None and min_value < 0:
            raise ValueError("min_value must be non-negative")

        super().__init__(min_value=min_value, **options)


class NegativeIntegerField(IntegerField):
    """Field for negative integer values.

    Examples:
        >>> class Temperature(Model):
        ...     degrees = NegativeIntegerField(max_value=-1)
    """

    def __init__(self, *, max_value: Optional[int] = 0, **options: Any) -> None:
        """Initialize negative integer field.

        Args:
            max_value: Maximum allowed value (must be <= 0)
            **options: Additional field options

        Raises:
            ValueError: If max_value is positive
        """
        if max_value is not None and max_value > 0:
            raise ValueError("max_value must be non-positive")

        super().__init__(max_value=max_value, **options)


class AutoIncrementField(IntegerField):
    """Auto-incrementing integer field.

    Examples:
        >>> class User(Model):
        ...     id = AutoIncrementField(primary_key=True)
    """

    def __init__(self, *, primary_key: bool = True, **options: Any) -> None:
        """Initialize auto-increment field.

        Args:
            primary_key: Whether this field is the primary key
            **options: Additional field options
        """
        super().__init__(min_value=1, **options)

        # Update backend options for auto-increment
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "int",
                    "autoIncrement": True,
                },
                "postgres": {
                    "type": "SERIAL" if primary_key else "INTEGER",
                    "autoIncrement": True,
                },
                "mysql": {
                    "type": "INTEGER",
                    "autoIncrement": True,
                },
            }
        )
