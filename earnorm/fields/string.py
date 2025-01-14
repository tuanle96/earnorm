"""String field types."""

from typing import Any, List, Optional

from earnorm.fields.base import Field
from earnorm.validators import (
    ValidatorFunc,
    validate_email,
    validate_length,
    validate_regex,
)


class StringField(Field[str]):
    """String field."""

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
        strip: bool = True,
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
            strip: Whether to strip whitespace from value
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.strip = strip

        # Add validators
        if min_length is not None or max_length is not None:
            self.validators.append(validate_length(min_length, max_length))
        if pattern is not None:
            self.validators.append(validate_regex(pattern))

    def convert(self, value: Any) -> str:
        """Convert value to string."""
        if value is None:
            return ""
        result = str(value)
        if self.strip:
            result = result.strip()
        return result

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python string to MongoDB string."""
        if value is None:
            return ""
        if self.strip:
            value = value.strip()
        return str(value)

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python string."""
        if value is None:
            return ""
        result = str(value)
        if self.strip:
            result = result.strip()
        return result


class EmailStringField(StringField):
    """Email string field."""

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.validators.append(validate_email)


class PhoneStringField(StringField):
    """Phone string field."""

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            pattern=r"^\+?[1-9]\d{1,14}$",  # E.164 format
            **kwargs,
        )


class PasswordStringField(StringField):
    """Password string field."""

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_length: int = 8,
        pattern: str = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$",
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_length: Minimum password length
            pattern: Regex pattern for password requirements
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            min_length=min_length,
            pattern=pattern,
            **kwargs,
        )
