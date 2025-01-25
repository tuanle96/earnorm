"""Exception definitions for EarnORM.

This module defines all custom exceptions used throughout EarnORM.
These exceptions provide detailed error information and help with error handling.

Examples:
    ```python
    try:
        await db.users.find_one({"_id": "invalid"})
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except OperationError as e:
        print(f"Operation failed: {e}")
    ```
"""

from typing import Any, Optional


class EarnBaseError(Exception):
    """Base class for all EarnORM-related errors."""

    def __init__(self, message: str, context: Optional[Any] = None) -> None:
        """Initialize base error.

        Args:
            message: Error message
            context: Additional context
        """
        super().__init__(message)
        self.context = context


# Database-related errors
class DatabaseError(EarnBaseError):
    """Base class for database-related errors."""

    pass


class PoolError(DatabaseError):
    """Error raised when pool operation fails."""

    pass


class ConnectionError(DatabaseError):
    """Error raised when connection fails."""

    pass


class DatabaseConnectionError(ConnectionError):
    """Error raised when database connection fails."""

    pass


class OperationError(DatabaseError):
    """Error raised when database operation fails."""

    pass


class DatabaseValidationError(DatabaseError):
    """Error raised when database validation fails."""

    pass


class ConfigurationError(DatabaseError):
    """Error raised when configuration is invalid."""

    pass


class TimeoutError(DatabaseError):
    """Error raised when operation times out."""

    pass


class RetryError(DatabaseError):
    """Error raised when retry attempts are exhausted."""

    pass


class CircuitBreakerError(DatabaseError):
    """Error raised when circuit breaker prevents operation."""

    pass


class PoolExhaustedError(DatabaseError):
    """Error raised when connection pool is exhausted."""

    pass


class StaleConnectionError(DatabaseError):
    """Error raised when connection is stale."""

    pass


class TransactionError(DatabaseError):
    """Error raised when transaction operation fails."""

    pass


class SessionError(DatabaseError):
    """Error raised when session operation fails."""

    pass


class BulkOperationError(DatabaseError):
    """Error raised when bulk operation fails."""

    pass


# Model-related errors
class ModelError(EarnBaseError):
    """Base class for model-related errors."""

    pass


class ModelValidationError(ModelError):
    """Error raised when model validation fails."""

    pass


class SerializationError(ModelError):
    """Error raised when model serialization fails."""

    pass


class DeserializationError(ModelError):
    """Error raised when model deserialization fails."""

    pass


class RelationshipError(ModelError):
    """Error raised when model relationship operation fails."""

    pass


class QueryError(ModelError):
    """Error raised when model query operation fails."""

    pass
