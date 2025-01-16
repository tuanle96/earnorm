"""Cache exceptions.

This module defines the exception hierarchy for the cache system:

Hierarchy:
    CacheError
    ├── ConnectionError
    ├── LockError
    ├── SerializationError
    └── ValidationError

Examples:
    ```python
    from earnorm.cache.core.exceptions import CacheError, ConnectionError

    try:
        await cache.connect()
    except ConnectionError as e:
        print(f"Failed to connect: {e}")
    except CacheError as e:
        print(f"Cache error: {e}")
    ```
"""


class CacheError(Exception):
    """Base cache exception.

    All cache-related exceptions inherit from this class.

    Args:
        message: Error message describing the issue

    Examples:
        ```python
        raise CacheError("Cache operation failed")
        ```
    """

    def __init__(self, message: str) -> None:
        """Initialize exception.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)


class ConnectionError(CacheError):
    """Cache connection error.

    Raised when connection to cache server fails.

    Examples:
        ```python
        raise ConnectionError("Failed to connect to Redis")
        ```
    """

    pass


class LockError(CacheError):
    """Lock operation error.

    Raised when distributed lock operations fail.

    Examples:
        ```python
        raise LockError("Failed to acquire lock")
        ```
    """

    pass


class SerializationError(CacheError):
    """Value serialization error.

    Raised when value cannot be serialized/deserialized.

    Examples:
        ```python
        raise SerializationError("Failed to serialize value")
        ```
    """

    pass


class ValidationError(CacheError):
    """Value validation error.

    Raised when value fails validation.

    Examples:
        ```python
        raise ValidationError("Invalid value type")
        ```
    """

    pass
