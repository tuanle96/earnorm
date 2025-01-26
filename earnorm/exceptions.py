"""Global exceptions for EarnORM.

This module provides all custom exceptions used throughout EarnORM.
"""

from typing import Optional


class EarnORMError(Exception):
    """Base class for all EarnORM errors."""

    def __init__(self, message: str) -> None:
        """Initialize EarnORM error.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)


# Field-related exceptions
class FieldError(EarnORMError):
    """Base class for field-related errors.

    Attributes:
        message: Error message
        field_name: Name of field that caused the error
        code: Error code for identifying error type
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str,
        code: Optional[str] = None,
    ) -> None:
        """Initialize field error.

        Args:
            message: Error message
            field_name: Field name
            code: Error code for identifying error type
        """
        self.field_name = field_name
        self.code = code or "field_error"
        super().__init__(f"{field_name}: {message} (code={self.code})")


class FieldValidationError(FieldError):
    """Error raised when field validation fails.

    This error is raised when a field value fails validation,
    either due to type mismatch, constraint violation, or
    custom validation rules.

    Attributes:
        message: Error message
        field_name: Name of field that caused the error
        code: Error code for identifying validation error type
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str,
        code: Optional[str] = "validation_error",
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Field name
            code: Error code for identifying validation error type
        """
        super().__init__(message, field_name=field_name, code=code)


class ModelResolutionError(FieldError):
    """Error raised when model resolution fails.

    This error is raised when a model class cannot be resolved,
    typically when trying to resolve a model name to its class
    without having access to the model registry.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize model resolution error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="model_resolution_error")


class ModelNotFoundError(FieldError):
    """Error raised when model is not found.

    This error is raised when a model class cannot be found
    in the model registry, typically when trying to resolve
    a model name that doesn't exist.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize model not found error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="model_not_found_error")


# Database-related exceptions
class DatabaseError(EarnORMError):
    """Base class for database-related errors."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize database error.

        Args:
            message: Error message
            backend: Database backend name
        """
        self.backend = backend
        super().__init__(f"{backend}: {message}")


class ConnectionError(DatabaseError):
    """Error raised when database connection fails."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize connection error.

        Args:
            message: Error message
            backend: Database backend name
        """
        super().__init__(message, backend=backend)


class QueryError(DatabaseError):
    """Error raised when database query fails."""

    def __init__(self, message: str, *, backend: str, query: str) -> None:
        """Initialize query error.

        Args:
            message: Error message
            backend: Database backend name
            query: Failed query
        """
        self.query = query
        super().__init__(f"{message} (query={query})", backend=backend)


# Cache-related exceptions
class CacheError(EarnORMError):
    """Base class for cache-related errors."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize cache error.

        Args:
            message: Error message
            backend: Cache backend name
        """
        self.backend = backend
        super().__init__(f"{backend}: {message}")


class CacheConnectionError(CacheError):
    """Error raised when cache connection fails."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize cache connection error.

        Args:
            message: Error message
            backend: Cache backend name
        """
        super().__init__(message, backend=backend)


class CacheKeyError(CacheError):
    """Error raised when cache key operation fails."""

    def __init__(self, message: str, *, backend: str, key: str) -> None:
        """Initialize cache key error.

        Args:
            message: Error message
            backend: Cache backend name
            key: Failed key
        """
        self.key = key
        super().__init__(f"{message} (key={key})", backend=backend)
