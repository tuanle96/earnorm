"""Base interfaces for connection pool management."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PoolManager(Protocol):
    """Protocol for pool manager."""

    async def get_collection(self, name: str) -> Any:
        """Get collection by name.

        Args:
            name: Collection name

        Returns:
            Collection instance
        """
        ...
