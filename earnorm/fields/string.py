"""String field types for EarnORM."""

from typing import Any, List, Optional, Pattern, Union

from earnorm.fields.base import Field, ValidatorFunc
from earnorm.validators import validate_email, validate_length, validate_regex


class StringField(Field[str]):
    """String field with validation attributes."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        strip: bool = True,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[Union[str, Pattern[str]]] = None,
        validators: Optional[List[ValidatorFunc]] = None,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            default: Default value
            index: Whether to create index
            unique: Whether field should be unique
            strip: Whether to strip whitespace
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regex pattern for validation
            validators: Additional validators
        """
        # Build validators list
        field_validators = validators or []

        # Add length validator if specified
        if min_length is not None or max_length is not None:
            field_validators.append(validate_length(min_length, max_length))

        # Add regex validator if specified
        if pattern is not None:
            field_validators.append(validate_regex(pattern))

        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            validators=field_validators,
        )
        self.strip = strip
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

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
        result = str(value)
        if self.strip:
            result = result.strip()
        return result

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python string."""
        if value is None:
            return ""
        result = str(value)
        if self.strip:
            result = result.strip()
        return result


class EmailStringField(StringField):
    """Email string field with validation."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        strip: bool = True,
        validators: Optional[List[ValidatorFunc]] = None,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            default: Default value
            index: Whether to create index
            unique: Whether field should be unique
            strip: Whether to strip whitespace
            validators: Additional validators
        """
        # Add email validator
        field_validators = validators or []
        field_validators.append(validate_email)

        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            strip=strip,
            validators=field_validators,
        )

    def convert(self, value: Any) -> str:
        """Convert value to email."""
        result = super().convert(value)
        if not result:
            return ""
        return result.lower()

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python email to MongoDB string."""
        result = super().to_mongo(value)
        if not result:
            return ""
        return result.lower()

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python email."""
        result = super().from_mongo(value)
        if not result:
            return ""
        return result.lower()


class PhoneStringField(StringField):
    """Phone string field with validation."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        strip: bool = True,
        validators: Optional[List[ValidatorFunc]] = None,
        pattern: str = r"^\+?1?\d{9,15}$",
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            default: Default value
            index: Whether to create index
            unique: Whether field should be unique
            strip: Whether to strip whitespace
            validators: Additional validators
            pattern: Phone number regex pattern
        """
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            strip=strip,
            pattern=pattern,
            validators=validators,
        )

    def convert(self, value: Any) -> str:
        """Convert value to phone number."""
        result = super().convert(value)
        if not result:
            return ""
        # Remove all non-digit characters
        return "".join(filter(str.isdigit, result))

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python phone number to MongoDB string."""
        result = super().to_mongo(value)
        if not result:
            return ""
        # Remove all non-digit characters
        return "".join(filter(str.isdigit, result))

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python phone number."""
        result = super().from_mongo(value)
        if not result:
            return ""
        # Remove all non-digit characters
        return "".join(filter(str.isdigit, result))


class PasswordStringField(StringField):
    """Password string field with validation."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        strip: bool = True,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        validators: Optional[List[ValidatorFunc]] = None,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            default: Default value
            index: Whether to create index
            unique: Whether field should be unique
            strip: Whether to strip whitespace
            min_length: Minimum password length
            require_uppercase: Require uppercase letter
            require_lowercase: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            validators: Additional validators
        """
        # Build password pattern
        pattern_parts: List[str] = []
        if require_uppercase:
            pattern_parts.append(r"(?=.*[A-Z])")
        if require_lowercase:
            pattern_parts.append(r"(?=.*[a-z])")
        if require_digit:
            pattern_parts.append(r"(?=.*\d)")
        if require_special:
            pattern_parts.append(r"(?=.*[!@#$%^&*(),.?\":{}|<>])")
        pattern_parts.append(rf".{{{min_length},}}")
        pattern = "".join(pattern_parts)

        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            strip=strip,
            min_length=min_length,
            pattern=pattern,
            validators=validators,
        )
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
