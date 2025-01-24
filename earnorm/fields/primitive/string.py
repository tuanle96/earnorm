"""String field implementation.

This module provides string field types for text data.
It supports:
- String length validation
- Pattern matching with regex
- Case sensitivity options
- String transformations (lower, upper, title, capitalize)
- Common string formats (email, url)
- Whitespace stripping

Examples:
    >>> class User(Model):
    ...     username = StringField(min_length=3, max_length=30, pattern=r'^[a-zA-Z0-9_]+$')
    ...     email = EmailField(required=True)
    ...     website = URLField()
    ...     bio = TextField(max_length=1000)

    >>> user = User()
    >>> await user.validate() # Raises ValidationError for required email
    >>> user.email = "invalid"  # Raises ValidationError for invalid email format
    >>> user.email = "user@example.com"  # Valid
    >>> user.username = "user.1"  # Raises ValidationError for invalid pattern
    >>> user.username = "user_1"  # Valid
"""

import re
from typing import Any, Optional, Pattern, Union

from earnorm.fields.base import Field, ValidationError


class StringField(Field[str]):
    """Field for string values.

    This field handles:
    - String length validation (min/max)
    - Pattern matching with regex
    - Case sensitivity
    - Whitespace stripping
    - String transformations

    Attributes:
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regular expression pattern for validation
        case_sensitive: Whether string matching is case sensitive
        strip: Whether to strip whitespace
        transform: String transformation ('lower', 'upper', 'title', 'capitalize')

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a string
            - min_length: String length is less than min_length
            - max_length: String length exceeds max_length
            - invalid_pattern: String does not match pattern
            - conversion_failed: Value cannot be converted to string

    Examples:
        >>> name = StringField(min_length=2, max_length=50)
        >>> await name.validate("A")  # Raises ValidationError(code="min_length")
        >>> await name.validate("Bob")  # Valid

        >>> username = StringField(pattern=r'^[a-z0-9_]+$')
        >>> await username.validate("User.1")  # Raises ValidationError(code="invalid_pattern")
        >>> await username.validate("user_1")  # Valid

        >>> email = StringField(transform="lower", strip=True)
        >>> await email.convert(" Test@Example.com ")  # Returns "test@example.com"
    """

    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[Union[str, Pattern[str]]] = None,
        case_sensitive: bool = True,
        strip: bool = True,
        transform: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize string field.

        Args:
            min_length: Minimum string length (inclusive)
            max_length: Maximum string length (inclusive)
            pattern: Regular expression pattern for validation
            case_sensitive: Whether string matching is case sensitive
            strip: Whether to strip whitespace from input
            transform: String transformation ('lower', 'upper', 'title', 'capitalize')
            **options: Additional field options

        Examples:
            >>> name = StringField(min_length=2, max_length=50)
            >>> username = StringField(pattern=r'^[a-z0-9_]+$')
            >>> email = StringField(transform="lower", strip=True)
        """
        super().__init__(**options)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.case_sensitive = case_sensitive
        self.strip = strip
        self.transform = transform

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "string",
                    "maxLength": max_length,
                },
                "postgres": {
                    "type": "VARCHAR",
                    "length": max_length,
                },
                "mysql": {
                    "type": "VARCHAR",
                    "length": max_length,
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate string value.

        Validates:
        - Type is string
        - Length constraints
        - Pattern matching
        - Required/optional

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a string
                - min_length: String length is less than min_length
                - max_length: String length exceeds max_length
                - invalid_pattern: String does not match pattern

        Examples:
            >>> field = StringField(min_length=2, pattern=r'^[a-z]+$')
            >>> await field.validate("A")  # Raises ValidationError(code="min_length")
            >>> await field.validate("Ab")  # Raises ValidationError(code="invalid_pattern")
            >>> await field.validate("ab")  # Valid
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, str):
                raise ValidationError(
                    message=f"Value must be a string, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.strip:
                value = value.strip()

            if self.min_length is not None and len(value) < self.min_length:
                raise ValidationError(
                    message=f"String length must be at least {self.min_length}, got {len(value)}",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value) > self.max_length:
                raise ValidationError(
                    message=f"String length must be at most {self.max_length}, got {len(value)}",
                    field_name=self.name,
                    code="max_length",
                )

            if self.pattern is not None:
                if not self.pattern.match(value):
                    raise ValidationError(
                        message=f"String must match pattern {self.pattern.pattern}",
                        field_name=self.name,
                        code="invalid_pattern",
                    )

    async def convert(self, value: Any) -> Optional[str]:
        """Convert value to string.

        Handles:
        - None values
        - String conversion
        - Whitespace stripping
        - String transformation

        Args:
            value: Value to convert

        Returns:
            Converted string value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = StringField(transform="lower", strip=True)
            >>> await field.convert(" Test ")  # Returns "test"
            >>> await field.convert(123)  # Returns "123"
            >>> await field.convert(None)  # Returns None
        """
        if value is None:
            return self.default

        try:
            value = str(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert {type(value).__name__} to string: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )

        if self.strip:
            value = value.strip()

        if self.transform:
            if self.transform == "lower":
                value = value.lower()
            elif self.transform == "upper":
                value = value.upper()
            elif self.transform == "title":
                value = value.title()
            elif self.transform == "capitalize":
                value = value.capitalize()

        return value

    async def to_db(self, value: Optional[str], backend: str) -> Optional[str]:
        """Convert string to database format.

        Args:
            value: String value to convert
            backend: Database backend type

        Returns:
            Converted string value or None

        Examples:
            >>> field = StringField(case_sensitive=False)
            >>> await field.to_db("Test", "mongodb")  # Returns "test"
            >>> await field.to_db(None, "mongodb")  # Returns None
        """
        if value is None:
            return None

        if not self.case_sensitive:
            value = value.lower()

        return value

    async def from_db(self, value: Any, backend: str) -> Optional[str]:
        """Convert database value to string.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted string value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = StringField()
            >>> await field.from_db("test", "mongodb")  # Returns "test"
            >>> await field.from_db(None, "mongodb")  # Returns None
        """
        if value is None:
            return None

        try:
            return str(value)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert database value to string: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )


class EmailField(StringField):
    """Field for email addresses.

    Examples:
        >>> class User(Model):
        ...     email = EmailField(required=True)
        ...     backup_email = EmailField()
    """

    def __init__(self, **options: Any) -> None:
        """Initialize email field.

        Args:
            **options: Additional field options
        """
        super().__init__(
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            case_sensitive=False,
            strip=True,
            transform="lower",
            **options,
        )


class URLField(StringField):
    """Field for URLs.

    Examples:
        >>> class Website(Model):
        ...     url = URLField(required=True)
        ...     favicon = URLField()
    """

    def __init__(self, *, require_tld: bool = True, **options: Any) -> None:
        """Initialize URL field.

        Args:
            require_tld: Whether to require a top-level domain
            **options: Additional field options
        """
        pattern = (
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$"  # path
        )
        if not require_tld:
            pattern = pattern.replace(r"[A-Z]{2,6}", r"[A-Z]{2,}")

        super().__init__(
            pattern=pattern,
            case_sensitive=False,
            strip=True,
            transform="lower",
            **options,
        )


class PasswordField(StringField):
    """Field for passwords with hashing.

    Examples:
        >>> class User(Model):
        ...     password = PasswordField(
        ...         min_length=8,
        ...         require_upper=True,
        ...         require_lower=True,
        ...         require_digit=True,
        ...         require_special=True,
        ...     )
    """

    def __init__(
        self,
        *,
        min_length: int = 8,
        require_upper: bool = True,
        require_lower: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        **options: Any,
    ) -> None:
        """Initialize password field.

        Args:
            min_length: Minimum password length
            require_upper: Require uppercase letter
            require_lower: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            **options: Additional field options
        """
        pattern_parts: list[str] = []
        if require_upper:
            pattern_parts.append(r"(?=.*[A-Z])")
        if require_lower:
            pattern_parts.append(r"(?=.*[a-z])")
        if require_digit:
            pattern_parts.append(r"(?=.*\d)")
        if require_special:
            pattern_parts.append(r'(?=.*[!@#$%^&*(),.?":{}|<>])')

        pattern = (
            f"{''.join(pattern_parts)}"
            rf"[A-Za-z\d!@#$%^&*(),.?\":{{}}|<>]{{{min_length},}}"
        )

        super().__init__(
            min_length=min_length,
            pattern=pattern,
            strip=True,
            **options,
        )

    async def to_db(self, value: Optional[str], backend: str) -> Optional[str]:
        """Convert password to database format.

        Args:
            value: Password value
            backend: Database backend type

        Returns:
            Hashed password
        """
        if value is None:
            return None

        # TODO: Implement password hashing
        return value


class TextField(StringField):
    """Field for long text content.

    Examples:
        >>> class Article(Model):
        ...     title = StringField(max_length=200)
        ...     content = TextField()
        ...     summary = TextField(max_length=500)
    """

    def __init__(self, **options: Any) -> None:
        """Initialize text field.

        Args:
            **options: Additional field options
        """
        super().__init__(strip=True, **options)

        # Update backend options for text type
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "string",
                },
                "postgres": {
                    "type": "TEXT",
                },
                "mysql": {
                    "type": "TEXT",
                },
            }
        )
