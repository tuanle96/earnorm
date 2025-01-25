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

from typing import Any, Dict, Optional


class CacheError(Exception):
    """Base exception for cache operations.

    This exception is raised when cache operation fails.
    It provides context about the operation and error.

    Features:
    - Operation context
    - Error details
    - Metadata

    Examples:
        ```python
        # Basic error
        raise CacheError("Failed to get value")

        # Error with operation
        raise CacheError("Failed to get value", operation="get")

        # Error with key
        raise CacheError("Failed to get value", key="user:123")

        # Error with metadata
        raise CacheError(
            "Failed to get value",
            operation="get",
            key="user:123",
            metadata={"ttl": 300}
        )
        ```
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize cache error.

        Args:
            message: Error message
            operation: Optional operation name
            key: Optional cache key
            metadata: Optional metadata dictionary
        """
        self.message = message
        self.operation = operation
        self.key = key
        self.metadata = metadata or {}
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message.

        Returns:
            str: Formatted error message
        """
        parts = [self.message]
        if self.operation:
            parts.append(f"operation={self.operation}")
        if self.key:
            parts.append(f"key={self.key}")
        if self.metadata:
            parts.append(f"metadata={self.metadata}")
        return " ".join(parts)


class CacheConnectionError(CacheError):
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
