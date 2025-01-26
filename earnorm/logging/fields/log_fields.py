"""Custom fields for logging module.

This module provides custom field types for the logging module.

Examples:
    >>> class Log(BaseModel):
    ...     level = LogLevelField(required=True)
    ...     message = StringField(required=True)
"""

from typing import Any, ClassVar, Set

from earnorm.fields import StringField
from earnorm.logging.exceptions import LogLevelError


class LogLevelField(StringField):
    """Field for log levels with validation.

    This field ensures that log levels are one of the valid values:
    DEBUG, INFO, WARNING, ERROR, or CRITICAL.

    Examples:
        >>> log = Log(level="INFO", message="Test")  # Valid
        >>> log = Log(level="INVALID")  # Raises LogLevelError
    """

    VALID_LEVELS: ClassVar[Set[str]] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    async def validate(self, value: Any) -> None:
        """Validate that the value is a valid log level.

        Args:
            value: Value to validate

        Raises:
            LogLevelError: If value is not a valid log level
        """
        await super().validate(value)
        if value not in self.VALID_LEVELS:
            raise LogLevelError(
                f"Invalid log level: {value}. "
                f"Must be one of: {', '.join(sorted(self.VALID_LEVELS))}"
            )
