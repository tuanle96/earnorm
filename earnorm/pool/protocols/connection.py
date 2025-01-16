"""Connection protocol definition."""

from typing import Any, Protocol


class ConnectionProtocol(Protocol):
    """Protocol for database connections."""

    @property
    def created_at(self) -> float:
        """Get connection creation timestamp."""
        ...

    @property
    def last_used_at(self) -> float:
        """Get last used timestamp."""
        ...

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        ...

    @property
    def lifetime(self) -> float:
        """Get lifetime in seconds."""
        ...

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        ...

    def touch(self) -> None:
        """Update last used timestamp."""
        ...

    async def ping(self) -> bool:
        """Check connection health.

        Returns:
            True if connection is healthy
        """
        ...

    async def close(self) -> None:
        """Close connection."""
        ...

    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute database operation.

        Args:
            operation: Operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result
        """
        ...
