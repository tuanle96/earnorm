"""Field pool manager implementation.

This module provides the field pool manager for handling multiple field pools.
It supports:
- Multiple pool management
- Pool creation and deletion
- Resource cleanup
- Memory optimization
- Thread safety

Examples:
    >>> manager = FieldPoolManager()
    >>> pool = manager.create_pool("my_pool")
    >>> field = StringField()
    >>> pool.add(field)
    >>> pool = manager.get_pool("my_pool")
    >>> manager.remove_pool("my_pool")
"""

from threading import Lock
from typing import Dict, Optional, Set

from earnorm.fields.pool.base import FieldPool


class FieldPoolManager:
    """Manager for handling multiple field pools.

    Attributes:
        pools: Dictionary mapping pool names to pool instances
        _lock: Thread lock for synchronization
    """

    def __init__(self) -> None:
        """Initialize field pool manager."""
        self.pools: Dict[str, FieldPool] = {}
        self._lock = Lock()

    def create_pool(self, name: str) -> FieldPool:
        """Create new field pool.

        Args:
            name: Name of pool to create

        Returns:
            Created pool instance

        Raises:
            ValueError: If pool with name already exists
        """
        with self._lock:
            if name in self.pools:
                raise ValueError(f"Pool {name} already exists")
            pool = FieldPool()
            self.pools[name] = pool
            return pool

    def get_pool(self, name: str) -> Optional[FieldPool]:
        """Get field pool by name.

        Args:
            name: Name of pool to get

        Returns:
            Pool instance if found, None otherwise
        """
        with self._lock:
            return self.pools.get(name)

    def remove_pool(self, name: str) -> None:
        """Remove field pool.

        Args:
            name: Name of pool to remove
        """
        with self._lock:
            if name in self.pools:
                pool = self.pools[name]
                pool.clear()
                del self.pools[name]

    def clear(self) -> None:
        """Clear all field pools."""
        with self._lock:
            for pool in self.pools.values():
                pool.clear()
            self.pools.clear()

    def cleanup(self) -> None:
        """Clean up unused field pools."""
        with self._lock:
            for pool in self.pools.values():
                pool.cleanup()

    def get_pool_names(self) -> Set[str]:
        """Get names of all field pools.

        Returns:
            Set of pool names
        """
        with self._lock:
            return set(self.pools.keys())

    def has_pool(self, name: str) -> bool:
        """Check if pool exists.

        Args:
            name: Name of pool to check

        Returns:
            True if pool exists, False otherwise
        """
        with self._lock:
            return name in self.pools

    async def setup(self) -> None:
        """Set up all field pools."""
        with self._lock:
            for pool in self.pools.values():
                await pool.setup()

    async def cleanup_async(self) -> None:
        """Clean up all field pools asynchronously."""
        with self._lock:
            for pool in self.pools.values():
                await pool.cleanup_async()
            self.cleanup()
