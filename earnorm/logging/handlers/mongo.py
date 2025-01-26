"""MongoDB handler for logging.

This module provides a handler for storing logs in MongoDB with
support for batching and automatic cleanup.

Examples:
    >>> handler = MongoHandler(batch_size=100)
    >>> await handler.handle({
    ...     'level': 'INFO',
    ...     'message': 'Test message',
    ...     'module': 'test_module'
    ... })
"""

from typing import Any, Dict, Optional

from earnorm.logging.handlers.base import BaseHandler
from earnorm.logging.models.log import Log


class MongoHandler(BaseHandler):
    """Handler for storing logs in MongoDB.

    This handler supports:
    - Batch inserts for better performance
    - Automatic cleanup of old logs
    - Custom field mapping

    Attributes:
        batch_size: Number of logs to batch before inserting
        ttl_days: Number of days to keep logs (0 for no expiry)
    """

    def __init__(
        self,
        batch_size: int = 100,
        ttl_days: int = 30,
        format_string: Optional[str] = None,
    ) -> None:
        """Initialize the MongoDB handler.

        Args:
            batch_size: Number of logs to batch before inserting
            ttl_days: Number of days to keep logs (0 for no expiry)
            format_string: Format string for log messages
        """
        super().__init__(batch_size, format_string)
        self.ttl_days = ttl_days

    async def handle(self, log_entry: Dict[str, Any]) -> None:
        """Handle a log entry by storing it in MongoDB.

        Args:
            log_entry: Log entry to store
        """
        self._batch.append(log_entry)
        if len(self._batch) >= self.batch_size:
            await self.flush()

    async def _flush_batch(self) -> None:
        """Flush the current batch of log entries to MongoDB."""
        if not self._batch:
            return

        # Create log entries
        for entry in self._batch:
            await Log.create(entry)

        # Clean up old logs if TTL is set
        if self.ttl_days > 0:
            await Log.cleanup_old_logs(days=self.ttl_days)

    async def close(self) -> None:
        """Close the handler and flush any remaining logs."""
        await self.flush()
