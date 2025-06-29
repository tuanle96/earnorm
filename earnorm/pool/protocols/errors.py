"""Error definitions for database operations.

This module defines custom exceptions for database operations.
These exceptions provide detailed error information and help with error handling.

Examples:
    ```python
    try:
        await connection.execute_typed(MongoOperation.FIND_ONE, {"_id": "invalid"})
    except ConnectionError as e:
        print(f"Connection failed: {e}")
    except OperationError as e:
        print(f"Operation failed: {e}")
    ```
"""

from typing import Any


class DatabaseError(Exception):
    """Base class for database-related errors."""

    def __init__(self, message: str, context: Any | None = None) -> None:
        """Initialize database error.

        Args:
            message: Error message
            context: Additional context
        """
        super().__init__(message)
        self.context = context


class PoolError(DatabaseError):
    """Error raised when pool operation fails."""

    pass


class ConnectionError(DatabaseError):
    """Error raised when connection fails."""

    pass


class OperationError(DatabaseError):
    """Raised when database operation fails."""

    pass


class ValidationError(DatabaseError):
    """Raised when validation fails."""

    pass


class ConfigurationError(DatabaseError):
    """Raised when configuration is invalid."""

    pass


class TimeoutError(DatabaseError):
    """Raised when operation times out."""

    pass


class RetryError(DatabaseError):
    """Error raised when retry attempts are exhausted."""

    pass


class CircuitBreakerError(DatabaseError):
    """Error raised when circuit breaker prevents operation."""

    pass


class PoolExhaustedError(DatabaseError):
    """Raised when connection pool is exhausted."""

    pass


class StaleConnectionError(DatabaseError):
    """Raised when connection is stale."""

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
