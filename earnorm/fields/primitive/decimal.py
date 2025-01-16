"""Decimal field type."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, List, Optional, Type, Union

from earnorm.fields.base import Field
from earnorm.validators import validate_range
from earnorm.validators.types import ValidatorFunc


class DecimalField(Field[Decimal]):
    """Decimal field.

    Examples:
        >>> price = DecimalField(required=True, precision=2)
        >>> price.convert("123.456")
        Decimal('123.46')
        >>> price.convert(123.456)
        Decimal('123.46')
        >>> price.convert(None)
        Decimal('0')

        # With range validation
        >>> rating = DecimalField(min_value=0, max_value=5, precision=1)
        >>> rating.convert(4.5)  # Valid
        Decimal('4.5')
        >>> rating.convert(5.5)  # Will raise ValidationError
        ValidationError: Value must be between 0 and 5
    """

    def _get_field_type(self) -> Type[Decimal]:
        """Get field type.

        Returns:
            Type object representing decimal type
        """
        return Decimal

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_value: Optional[Union[int, float, Decimal]] = None,
        max_value: Optional[Union[int, float, Decimal]] = None,
        precision: int = 2,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            precision: Number of decimal places
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.precision = precision
        if min_value is not None or max_value is not None:
            # Convert min/max values to float for validation
            min_float = float(min_value) if min_value is not None else None
            max_float = float(max_value) if max_value is not None else None
            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_range(min_float, max_float))  # type: ignore

    def convert(self, value: Any) -> Decimal:
        """Convert value to decimal.

        Args:
            value: Value to convert

        Returns:
            Converted decimal value or 0 if value is None

        Examples:
            >>> field = DecimalField(precision=2)
            >>> field.convert("123.456")
            Decimal('123.46')
            >>> field.convert(123.456)
            Decimal('123.46')
            >>> field.convert(None)
            Decimal('0')
        """
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value.quantize(
                Decimal(f"0.{'0' * self.precision}"), rounding=ROUND_HALF_UP
            )
        return Decimal(str(value)).quantize(
            Decimal(f"0.{'0' * self.precision}"), rounding=ROUND_HALF_UP
        )

    def to_mongo(self, value: Optional[Decimal]) -> Optional[float]:
        """Convert Python decimal to MongoDB decimal.

        Args:
            value: Decimal value to convert

        Returns:
            MongoDB float value or None if value is None

        Examples:
            >>> field = DecimalField(precision=2)
            >>> field.to_mongo(Decimal("123.456"))
            123.46
            >>> field.to_mongo(None)
            None
        """
        if value is None:
            return None
        return float(value)

    def from_mongo(self, value: Any) -> Decimal:
        """Convert MongoDB decimal to Python decimal.

        Args:
            value: MongoDB value to convert

        Returns:
            Python decimal value or 0 if value is None

        Examples:
            >>> field = DecimalField(precision=2)
            >>> field.from_mongo(123.456)
            Decimal('123.46')
            >>> field.from_mongo(None)
            Decimal('0')
        """
        if value is None:
            return Decimal("0")
        return Decimal(str(value)).quantize(
            Decimal(f"0.{'0' * self.precision}"), rounding=ROUND_HALF_UP
        )
