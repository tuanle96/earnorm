"""Enhanced character field types for EarnORM."""

from typing import Any, Optional

import phonenumbers
from pydantic import EmailStr

from earnorm.base.fields import StringField
from earnorm.value_objects import Country


class CharField(StringField):
    """Enhanced string field with additional features."""

    def __init__(self, *, string: str, strip: bool = True, **kwargs: Any) -> None:
        """Initialize string field.

        Args:
            string: Field label
            strip: Whether to strip whitespace
            **kwargs: Additional field options
        """
        super().__init__(**kwargs)
        self.string = string
        self.strip = strip

    def convert(self, value: Any) -> str:
        """Convert value to string with stripping.

        Args:
            value: Value to convert

        Returns:
            str: Converted string
        """
        value = super().convert(value)
        if self.strip and isinstance(value, str):
            value = value.strip()
        return value


class EmailField(CharField):
    """Email field with validation."""

    def __init__(self, *, string: str, **kwargs: Any) -> None:
        """Initialize email field.

        Args:
            string: Field label
            **kwargs: Additional field options
        """
        super().__init__(
            string=string,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            **kwargs,
        )

    def validate(self, value: Optional[str]) -> None:
        """Validate email address.

        Args:
            value: Value to validate

        Raises:
            ValueError: If validation fails
        """
        super().validate(value)
        if value is not None:
            try:
                EmailStr.validate(value)
            except ValueError:
                raise ValueError(f"{self.string} is not a valid email address")


class PhoneField(CharField):
    """Phone number field with country-specific validation."""

    def __init__(
        self, *, string: str, country: Country = Country.INTERNATIONAL, **kwargs: Any
    ) -> None:
        """Initialize phone field.

        Args:
            string: Field label
            country: Country for validation
            **kwargs: Additional field options
        """
        super().__init__(string=string, **kwargs)
        self.country = country

    def validate(self, value: Optional[str]) -> None:
        """Validate phone number.

        Args:
            value: Value to validate

        Raises:
            ValueError: If validation fails
        """
        super().validate(value)
        if value is not None:
            try:
                number = phonenumbers.parse(value, self.country.code)
                if not phonenumbers.is_valid_number(number):
                    raise ValueError
            except Exception:
                raise ValueError(
                    f"{self.string} is not a valid phone number for {self.country.name}"
                )

    def convert(self, value: Any) -> str:
        """Convert phone number to E.164 format.

        Args:
            value: Value to convert

        Returns:
            str: Phone number in E.164 format
        """
        value = super().convert(value)
        if value:
            try:
                number = phonenumbers.parse(value, self.country.code)
                if phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(
                        number, phonenumbers.PhoneNumberFormat.E164
                    )
            except Exception:
                pass
        return value


class PasswordField(CharField):
    """Password field with hashing."""

    def __init__(
        self,
        *,
        string: str,
        min_length: int = 8,
        require_upper: bool = True,
        require_lower: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize password field.

        Args:
            string: Field label
            min_length: Minimum length
            require_upper: Require uppercase letter
            require_lower: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character
            **kwargs: Additional field options
        """
        super().__init__(
            string=string,
            min_length=min_length,
            **kwargs,
        )
        self.require_upper = require_upper
        self.require_lower = require_lower
        self.require_digit = require_digit
        self.require_special = require_special

    def validate(self, value: Optional[str]) -> None:
        """Validate password strength.

        Args:
            value: Value to validate

        Raises:
            ValueError: If validation fails
        """
        super().validate(value)
        if value is not None:
            if self.require_upper and not any(c.isupper() for c in value):
                raise ValueError(f"{self.string} must contain an uppercase letter")

            if self.require_lower and not any(c.islower() for c in value):
                raise ValueError(f"{self.string} must contain a lowercase letter")

            if self.require_digit and not any(c.isdigit() for c in value):
                raise ValueError(f"{self.string} must contain a digit")

            if self.require_special and not any(not c.isalnum() for c in value):
                raise ValueError(f"{self.string} must contain a special character")

    def to_mongo(self, value: Optional[str]) -> Optional[str]:
        """Hash password for storage.

        Args:
            value: Password to hash

        Returns:
            Optional[str]: Hashed password
        """
        if value is None:
            return None

        from ..security.encryption import hash_password

        return hash_password(value)
