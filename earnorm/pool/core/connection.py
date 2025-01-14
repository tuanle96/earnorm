"""Connection management for EarnORM."""

import time
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorClient


class Connection:
    """MongoDB connection wrapper."""

    def __init__(
        self,
        client: AsyncIOMotorClient[Dict[str, Any]],
        created_at: float = 0,
        last_used_at: float = 0,
    ) -> None:
        """Initialize connection.

        Args:
            client: Motor client instance
            created_at: Creation timestamp
            last_used_at: Last usage timestamp
        """
        self.client = client
        self.created_at = created_at or time.time()
        self.last_used_at = last_used_at or self.created_at
        self.is_closed = False

    @property
    def idle_time(self) -> float:
        """Get connection idle time in seconds."""
        return time.time() - self.last_used_at

    @property
    def lifetime(self) -> float:
        """Get connection lifetime in seconds."""
        return time.time() - self.created_at

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        return self.is_closed or not self.client

    async def ping(self) -> bool:
        """Ping connection to check health.

        Returns:
            True if connection is healthy
        """
        try:
            await self.client.admin.command("ping")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close connection."""
        if not self.is_closed:
            self.client.close()
            self.is_closed = True

    def touch(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = time.time()
