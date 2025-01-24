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

from typing import Any, Dict, Optional


class PoolError(Exception):
    """Base exception for all pool-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize pool error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.details = details or {}


class ConnectionError(PoolError):
    """Raised when connection fails."""

    pass


class OperationError(PoolError):
    """Raised when database operation fails."""

    pass


class ValidationError(PoolError):
    """Raised when validation fails."""

    pass


class ConfigurationError(PoolError):
    """Raised when configuration is invalid."""

    pass


class TimeoutError(PoolError):
    """Raised when operation times out."""

    pass


class RetryError(PoolError):
    """Raised when retry attempts are exhausted."""

    pass


class CircuitBreakerError(PoolError):
    """Raised when circuit breaker is open."""

    pass


class PoolExhaustedError(PoolError):
    """Raised when connection pool is exhausted."""

    pass


class StaleConnectionError(PoolError):
    """Raised when connection is stale."""

    pass
