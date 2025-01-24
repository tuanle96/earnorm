"""Decimal field type.

This module provides the DecimalField class for storing decimal values.
It includes:
- Decimal validation with precision and scale
- Decimal conversion from various types
- Range validation (min/max values)
- Precision and scale validation
- Database backend support (MongoDB, PostgreSQL, MySQL)
- Automatic type conversion

Examples:
    >>> from earnorm.fields.primitive.decimal import DecimalField
    >>>
    >>> class Product(Model):
    ...     price = DecimalField(precision=10, scale=2)
    ...     tax = DecimalField(precision=5, scale=2)
    ...     total = DecimalField(precision=10, scale=2, compute="_compute_total")

    >>> product = Product()
    >>> product.price = "123.45"  # Converts to Decimal('123.45')
    >>> product.tax = 12.5  # Converts to Decimal('12.50')
    >>> await product.validate()  # Validates precision and scale
    >>> product.price = "123.456"  # Raises ValidationError for invalid scale
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

from earnorm.fields.base import Field, ValidationError


class DecimalField(Field[Decimal]):
    """Field for storing decimal values.

    This field handles:
    - Decimal validation with precision and scale
    - Conversion from various numeric types
    - Range validation with min/max values
    - Database backend support
    - Automatic type conversion

    Attributes:
        precision: Total number of digits (integer + decimal)
        scale: Number of decimal places
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        default: Default value if None

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a decimal
            - invalid_precision: Value exceeds precision limit
            - invalid_scale: Value exceeds scale limit
            - min_value: Value is less than minimum
            - max_value: Value is greater than maximum
            - conversion_failed: Value cannot be converted to decimal

    Examples:
        >>> field = DecimalField(precision=5, scale=2)
        >>> await field.validate(Decimal("123.45"))  # Valid
        >>> await field.validate(Decimal("1234.5"))  # Raises ValidationError(code="invalid_precision")
        >>> await field.validate(Decimal("12.345"))  # Raises ValidationError(code="invalid_scale")

        >>> field = DecimalField(min_value=Decimal("0"), max_value=Decimal("100"))
        >>> await field.validate(Decimal("-1"))  # Raises ValidationError(code="min_value")
        >>> await field.validate(Decimal("101"))  # Raises ValidationError(code="max_value")
    """

    def __init__(
        self,
        *,
        precision: int = 10,
        scale: int = 2,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        default: Optional[Decimal] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize decimal field.

        Args:
            precision: Total number of digits (integer + decimal)
            scale: Number of decimal places
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            default: Default value if None
            **kwargs: Additional field options

        Examples:
            >>> field = DecimalField()  # Default precision=10, scale=2
            >>> field = DecimalField(precision=5, scale=2)  # Custom precision/scale
            >>> field = DecimalField(min_value=Decimal("0"))  # Non-negative values
        """
        super().__init__(**kwargs)
        self.precision = precision
        self.scale = scale
        self.min_value = min_value
        self.max_value = max_value
        self.default = default

        # Set backend options
        backend_opts: Dict[str, Dict[str, Any]] = {
            "mongodb": {
                "type": "decimal",
            },
            "postgres": {
                "type": f"DECIMAL({precision}, {scale})",
                "null": not getattr(self, "required", False),
                "default": str(default) if default else None,
            },
            "mysql": {
                "type": f"DECIMAL({precision}, {scale})",
                "null": not getattr(self, "required", False),
                "default": str(default) if default else None,
            },
        }

        # Add constraints if min/max values are set
        if min_value is not None or max_value is not None:
            constraints: List[str] = []
            if min_value is not None:
                constraints.append(f"{self.name} >= {min_value}")
            if max_value is not None:
                constraints.append(f"{self.name} <= {max_value}")
            check_constraint = " AND ".join(constraints)
            backend_opts["postgres"]["check"] = f"CHECK ({check_constraint})"
            backend_opts["mysql"]["check"] = f"CHECK ({check_constraint})"

        self.backend_options.update(backend_opts)

    async def validate(self, value: Any) -> None:
        """Validate decimal value.

        Validates:
        - Type is Decimal
        - Within precision limit
        - Within scale limit
        - Within min/max range
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a decimal
                - invalid_precision: Value exceeds precision limit
                - invalid_scale: Value exceeds scale limit
                - min_value: Value is less than minimum
                - max_value: Value is greater than maximum

        Examples:
            >>> field = DecimalField(precision=5, scale=2)
            >>> await field.validate(Decimal("123.45"))  # Valid
            >>> await field.validate(123.45)  # Raises ValidationError(code="invalid_type")
            >>> await field.validate(Decimal("1234.5"))  # Raises ValidationError(code="invalid_precision")
            >>> await field.validate(Decimal("12.345"))  # Raises ValidationError(code="invalid_scale")
        """
        await super().validate(value)
        if value is None:
            return

        if not isinstance(value, Decimal):
            raise ValidationError(
                message=f"Value must be a Decimal, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        # Check precision and scale
        str_value = str(value)
        if "." in str_value:
            integer_part, decimal_part = str_value.split(".")
            if len(decimal_part) > self.scale:
                raise ValidationError(
                    message=f"Value must have at most {self.scale} decimal places, got {len(decimal_part)}",
                    field_name=self.name,
                    code="invalid_scale",
                )
            if len(integer_part.lstrip("-")) + len(decimal_part) > self.precision:
                raise ValidationError(
                    message=f"Value must have at most {self.precision} total digits, got {len(integer_part.lstrip('-')) + len(decimal_part)}",
                    field_name=self.name,
                    code="invalid_precision",
                )
        else:
            if len(str_value.lstrip("-")) > self.precision:
                raise ValidationError(
                    message=f"Value must have at most {self.precision} total digits, got {len(str_value.lstrip('-'))}",
                    field_name=self.name,
                    code="invalid_precision",
                )

        # Check min/max values
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

    async def convert(self, value: Any) -> Optional[Decimal]:
        """Convert value to decimal.

        Handles:
        - None values
        - Decimal values
        - Integer/float values
        - String values

        Args:
            value: Value to convert

        Returns:
            Converted decimal value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = DecimalField()
            >>> await field.convert("123.45")  # Returns Decimal('123.45')
            >>> await field.convert(123)  # Returns Decimal('123')
            >>> await field.convert(123.45)  # Returns Decimal('123.45')
            >>> await field.convert(None)  # Returns default value
            >>> await field.convert("invalid")  # Raises ValidationError
        """
        if value is None:
            return self.default

        if isinstance(value, Decimal):
            return value

        try:
            if isinstance(value, (int, float, str)):
                return Decimal(str(value))
            raise TypeError(f"Cannot convert {type(value).__name__} to Decimal")
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValidationError(
                message=f"Cannot convert value to Decimal: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )

    async def to_db(
        self, value: Optional[Decimal], backend: str
    ) -> Union[None, str, Decimal]:
        """Convert decimal to database format.

        Args:
            value: Decimal value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            - None if value is None
            - Decimal for MongoDB (BSON Decimal128)
            - str for PostgreSQL and MySQL

        Examples:
            >>> field = DecimalField()
            >>> value = Decimal("123.45")
            >>> await field.to_db(value, "mongodb")  # Returns Decimal('123.45')
            >>> await field.to_db(value, "postgres")  # Returns "123.45"
            >>> await field.to_db(None, "mysql")  # Returns None
        """
        if value is None:
            return None

        # MongoDB stores decimals as BSON Decimal128
        if backend == "mongodb":
            return value

        # PostgreSQL and MySQL store decimals as strings
        if backend in ("postgres", "mysql"):
            return str(value)

        return value

    async def from_db(self, value: Any, backend: str) -> Optional[Decimal]:
        """Convert database value to decimal.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted decimal value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = DecimalField()
            >>> await field.from_db("123.45", "postgres")  # Returns Decimal('123.45')
            >>> await field.from_db(Decimal("123.45"), "mongodb")  # Returns Decimal('123.45')
            >>> await field.from_db(None, "mysql")  # Returns None
            >>> await field.from_db("invalid", "postgres")  # Raises ValidationError
        """
        if value is None:
            return None

        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, (int, float, str)):
                return Decimal(str(value))
            raise TypeError(f"Cannot convert {type(value).__name__} to Decimal")
        except (InvalidOperation, ValueError, TypeError) as e:
            raise ValidationError(
                message=f"Cannot convert database value to Decimal: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )
