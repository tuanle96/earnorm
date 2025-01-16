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

    def _get_field_type(self) -> Type[str]:
        """Get field type.

        Returns:
            Type object representing string type
        """
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
            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_length(min_length, max_length))  # type: ignore
        if pattern is not None:
            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_regex(pattern))  # type: ignore

    def convert(self, value: Any) -> str:
        """Convert value to string.

        Args:
            value: Value to convert

        Returns:
            Converted string value or empty string if value is None

        Examples:
            >>> field = StringField()
            >>> field.convert("hello")
            'hello'
            >>> field.convert(123)
            '123'
            >>> field.convert(None)
            ''
        """
        if value is None:
            return ""
        return str(value)

    def to_mongo(self, value: Optional[str]) -> Optional[str]:
        """Convert Python string to MongoDB string.

        Args:
            value: String value to convert

        Returns:
            MongoDB string value or None if value is None

        Examples:
            >>> field = StringField()
            >>> field.to_mongo("hello")
            'hello'
            >>> field.to_mongo(None)
            None
        """
        if value is None:
            return None
        return str(value)

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python string.

        Args:
            value: MongoDB value to convert

        Returns:
            Python string value or empty string if value is None

        Examples:
            >>> field = StringField()
            >>> field.from_mongo("hello")
            'hello'
            >>> field.from_mongo(None)
            ''
        """
        if value is None:
            return ""
        return str(value)

    def __repr__(self) -> str:
        """Get string representation of field."""
        return f"StringField(name={self.name}, required={self.required}, unique={self.unique}, default={self.default})"

    def __str__(self) -> str:
        """Get string representation of field."""
        return f"StringField(name={self.name}, required={self.required}, unique={self.unique}, default={self.default})"

    def __eq__(self, other: Any) -> bool:
        """Check if field is equal to another field."""
        return isinstance(other, StringField) and self.name == other.name

    def __hash__(self) -> int:
        """Get hash of field."""
        return hash(self.name)

    def test(self) -> None:
        """Test field."""
        print("test")
