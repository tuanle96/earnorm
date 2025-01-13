"""Character field types for EarnORM."""

from typing import Any, Optional

from earnorm.fields.base import Field


class CharField(Field[str]):
    """Character field."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        strip: bool = True,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
        )
        self.strip = strip

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


class EmailField(CharField):
    """Email field."""

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


class PhoneField(CharField):
    """Phone field."""

    def convert(self, value: Any) -> str:
        """Convert value to phone number."""
        result = super().convert(value)
        if not result:
            return ""
        # Remove all non-digit characters
        result = "".join(filter(str.isdigit, result))
        return result

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python phone number to MongoDB string."""
        result = super().to_mongo(value)
        if not result:
            return ""
        # Remove all non-digit characters
        result = "".join(filter(str.isdigit, result))
        return result

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python phone number."""
        result = super().from_mongo(value)
        if not result:
            return ""
        # Remove all non-digit characters
        result = "".join(filter(str.isdigit, result))
        return result


class PasswordField(CharField):
    """Password field."""

    def convert(self, value: Any) -> str:
        """Convert value to password."""
        if value is None:
            return ""
        return str(value)

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python password to MongoDB string."""
        if value is None:
            return ""
        return str(value)

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python password."""
        if value is None:
            return ""
        return str(value)
