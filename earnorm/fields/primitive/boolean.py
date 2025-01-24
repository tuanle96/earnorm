"""Boolean field implementation.

This module provides boolean field types for handling true/false values.
It supports:
- Boolean values (True/False)
- String representations ('true'/'false', 'yes'/'no', '1'/'0')
- Integer representations (1/0)
- Case-insensitive string matching (default)
- Custom true/false value sets
- Flexible value conversion

Examples:
    >>> class User(Model):
    ...     is_active = BooleanField(default=True)
    ...     is_staff = BooleanField(default=False)
    ...     has_agreed_terms = BooleanField(required=True)

    >>> user = User()
    >>> user.is_active = "yes"  # Converts to True
    >>> user.is_staff = 0  # Converts to False
    >>> await user.validate()  # Raises ValidationError for missing has_agreed_terms
    >>> user.has_agreed_terms = "invalid"  # Raises ValidationError for invalid value
"""

from typing import Any, Optional, Set, Union

from earnorm.fields.base import Field, ValidationError


class BooleanField(Field[bool]):
    """Field for boolean values.

    This field handles:
    - Boolean type validation
    - String/integer conversion
    - Custom true/false values
    - Case sensitivity options

    Attributes:
        true_values: Set of values that represent True
        false_values: Set of values that represent False
        case_sensitive: Whether string matching is case sensitive

    Raises:
        ValidationError: With codes:
            - invalid_type: Value cannot be converted to boolean
            - conversion_failed: Value cannot be converted to boolean

    Examples:
        >>> field = BooleanField()
        >>> await field.convert("yes")  # Returns True
        >>> await field.convert(0)  # Returns False
        >>> await field.convert(None)  # Returns default value

        >>> field = BooleanField(true_values={"1", "true"}, false_values={"0", "false"})
        >>> await field.convert("yes")  # Raises ValidationError

        >>> field = BooleanField(case_sensitive=True)
        >>> await field.convert("TRUE")  # Raises ValidationError
        >>> await field.convert("true")  # Returns True
    """

    # Default values that represent True/False
    DEFAULT_TRUE_VALUES: Set[Union[str, int, bool]] = {
        True,
        1,
        "true",
        "yes",
        "1",
        "on",
        "t",
        "y",
    }
    DEFAULT_FALSE_VALUES: Set[Union[str, int, bool]] = {
        False,
        0,
        "false",
        "no",
        "0",
        "off",
        "f",
        "n",
    }

    def __init__(
        self,
        *,
        true_values: Optional[Set[Union[str, int, bool]]] = None,
        false_values: Optional[Set[Union[str, int, bool]]] = None,
        case_sensitive: bool = False,
        **options: Any,
    ) -> None:
        """Initialize boolean field.

        Args:
            true_values: Set of values that represent True (defaults to DEFAULT_TRUE_VALUES)
            false_values: Set of values that represent False (defaults to DEFAULT_FALSE_VALUES)
            case_sensitive: Whether string matching is case sensitive (defaults to False)
            **options: Additional field options

        Examples:
            >>> field = BooleanField()  # Uses default true/false values
            >>> field = BooleanField(true_values={"1"}, false_values={"0"})  # Custom values
            >>> field = BooleanField(case_sensitive=True)  # Case-sensitive matching
        """
        super().__init__(**options)
        self.true_values = true_values or self.DEFAULT_TRUE_VALUES
        self.false_values = false_values or self.DEFAULT_FALSE_VALUES
        self.case_sensitive = case_sensitive

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "bool",
                },
                "postgres": {
                    "type": "BOOLEAN",
                },
                "mysql": {
                    "type": "BOOLEAN",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate boolean value.

        Validates:
        - Value can be converted to boolean
        - Value is in true_values or false_values if provided
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With code "invalid_type" if value cannot be converted

        Examples:
            >>> field = BooleanField()
            >>> await field.validate(True)  # Valid
            >>> await field.validate("yes")  # Valid
            >>> await field.validate("invalid")  # Raises ValidationError
            >>> await field.validate(None)  # Valid if not required
        """
        await super().validate(value)

        if value is not None:
            converted = self._convert_value(value)
            if converted is None:
                valid_values = sorted(
                    str(x) for x in (self.true_values | self.false_values)
                )
                raise ValidationError(
                    message=f"Value must be one of: {', '.join(valid_values)}, got {value!r}",
                    field_name=self.name,
                    code="invalid_type",
                )

    async def convert(self, value: Any) -> Optional[bool]:
        """Convert value to boolean.

        Handles:
        - None values
        - Boolean values
        - String values from true_values/false_values
        - Integer values from true_values/false_values

        Args:
            value: Value to convert

        Returns:
            Converted boolean value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = BooleanField()
            >>> await field.convert("yes")  # Returns True
            >>> await field.convert(0)  # Returns False
            >>> await field.convert("invalid")  # Raises ValidationError
            >>> await field.convert(None)  # Returns default value
        """
        if value is None:
            return self.default

        converted = self._convert_value(value)
        if converted is None:
            raise ValidationError(
                message=f"Cannot convert {value!r} to boolean, must be one of: {', '.join(str(x) for x in (self.true_values | self.false_values))}",
                field_name=self.name,
                code="conversion_failed",
            )
        return converted

    def _convert_value(self, value: Any) -> Optional[bool]:
        """Convert value to boolean using true/false value sets.

        This method handles:
        - String values with case sensitivity
        - Direct value comparison for non-strings
        - Custom true/false value sets

        Args:
            value: Value to convert

        Returns:
            True if value is in true_values
            False if value is in false_values
            None if value cannot be converted

        Examples:
            >>> field = BooleanField()
            >>> field._convert_value("yes")  # Returns True
            >>> field._convert_value(0)  # Returns False
            >>> field._convert_value("invalid")  # Returns None
        """
        # Handle string values
        if isinstance(value, str):
            value_str = value if self.case_sensitive else value.lower()
            # Check true values
            for true_val in self.true_values:
                if isinstance(true_val, str):
                    true_str = true_val if self.case_sensitive else true_val.lower()
                    if value_str == true_str:
                        return True
            # Check false values
            for false_val in self.false_values:
                if isinstance(false_val, str):
                    false_str = false_val if self.case_sensitive else false_val.lower()
                    if value_str == false_str:
                        return False
            return None

        # Handle non-string values
        if value in self.true_values:
            return True
        if value in self.false_values:
            return False
        return None

    async def to_db(self, value: Optional[bool], backend: str) -> Optional[bool]:
        """Convert boolean to database format.

        Args:
            value: Boolean value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database boolean value or None

        Examples:
            >>> field = BooleanField()
            >>> await field.to_db(True, "mongodb")  # Returns True
            >>> await field.to_db(None, "postgres")  # Returns None
        """
        return value

    async def from_db(self, value: Any, backend: str) -> Optional[bool]:
        """Convert database value to boolean.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted boolean value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = BooleanField()
            >>> await field.from_db(1, "mongodb")  # Returns True
            >>> await field.from_db(None, "postgres")  # Returns None
            >>> await field.from_db("invalid", "mysql")  # Raises ValidationError
        """
        if value is None:
            return None

        try:
            return bool(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert database value to boolean: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )
