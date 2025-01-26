"""Exceptions for logging module.

This module provides custom exceptions for the logging module.

Examples:
    >>> try:
    ...     log = Log(level="INVALID")
    ... except LogValidationError as e:
    ...     print(e)  # Invalid log level: INVALID
"""

from earnorm.exceptions import EarnORMError


class LogError(EarnORMError):
    """Base class for all logging errors."""


class LogValidationError(LogError):
    """Raised when log validation fails."""


class LogLevelError(LogValidationError):
    """Raised when an invalid log level is provided."""
