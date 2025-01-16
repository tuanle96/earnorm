"""String field type."""

from typing import Any, List, Optional, Type

from earnorm.fields.base import Field
from earnorm.validators import validate_length, validate_regex
from earnorm.validators.types import ValidatorFunc


class StringField(Field[str]):
    """String field.

    Examples:
        >>> name = StringField(required=True, min_length=2, max_length=50)
        >>> name.convert("John")
        'John'
        >>> name.convert(123)
        '123'
        >>> name.convert(None)
        ''

        # With regex pattern
        >>> username = StringField(pattern=r'^[a-zA-Z0-9_]+$')
        >>> username.convert("john_doe")  # Valid
        'john_doe'
        >>> username.convert("john@doe")  # Will raise ValidationError
        ValidationError: Value must match pattern '^[a-zA-Z0-9_]+$'
    """

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return str

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern to validate against
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        if min_length is not None or max_length is not None:
            self._metadata.validators.append(validate_length(min_length, max_length))
        if pattern is not None:
            self._metadata.validators.append(validate_regex(pattern))

    def convert(self, value: Any) -> str:
        """Convert value to string."""
        if value is None:
            return ""
        return str(value)

    def to_mongo(self, value: Optional[str]) -> Optional[str]:
        """Convert Python string to MongoDB string."""
        if value is None:
            return None
        return str(value)

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python string."""
        if value is None:
            return ""
        return str(value)
