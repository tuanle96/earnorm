"""Base connection implementation."""

import time
from typing import Any

from earnorm.pool.protocols.connection import ConnectionProtocol


class BaseConnection(ConnectionProtocol):
    """Base connection implementation."""

    def __init__(self) -> None:
        """Initialize connection."""
        self._created_at = time.time()
        self._last_used_at = self._created_at
        self._is_closed = False

    @property
    def created_at(self) -> float:
        """Get connection creation timestamp."""
        return self._created_at

    @property
    def last_used_at(self) -> float:
        """Get last used timestamp."""
        return self._last_used_at

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self._last_used_at

    @property
    def lifetime(self) -> float:
        """Get lifetime in seconds."""
        return time.time() - self._created_at

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        return self._is_closed

    def touch(self) -> None:
        """Update last used timestamp."""
        self._last_used_at = time.time()

    async def ping(self) -> bool:
        """Check connection health.

        Returns:
            True if connection is healthy
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Close connection."""
        self._is_closed = True

    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute database operation.

        Args:
            operation: Operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result
        """
        raise NotImplementedError
