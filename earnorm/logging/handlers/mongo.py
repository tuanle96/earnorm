"""MongoDB handler for storing logs in MongoDB."""

import asyncio
from typing import Any, Dict, List, Optional

from earnorm.logging.models.log import Log

from .base import BaseHandler


class MongoHandler(BaseHandler):
    """Handler for storing logs in MongoDB.

    This handler stores log entries in MongoDB using the Log model.
    It supports batching for better performance and includes retry logic
    for handling connection issues.

    Examples:
        >>> # Basic usage
        >>> handler = MongoHandler()
        >>> log_entry = {
        ...     'level': 'INFO',
        ...     'message': 'test message',
        ...     'module': 'test_module'
        ... }
        >>> await handler.emit(log_entry)  # Stores in MongoDB immediately

        >>> # Batch storage
        >>> handler = MongoHandler(batch_size=100)
        >>> for i in range(50):
        ...     await handler.handle({'message': f'message {i}'})
        >>> # Logs are stored when batch size is reached
        >>> await handler.close()  # Ensures remaining logs are stored
    """

    def __init__(
        self,
        batch_size: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        collection: Optional[str] = None,
    ):
        """Initialize the MongoDB handler.

        Args:
            batch_size: Optional batch size for batching log entries.
                If None, entries are stored immediately.
            max_retries: Maximum number of retries for failed operations.
            retry_delay: Delay in seconds between retries.
            collection: Optional collection name. If not provided, uses
                the default collection from the Log model.
        """
        super().__init__(batch_size)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.collection = collection

    async def _store_entries(self, entries: List[Dict[str, Any]]) -> None:
        """Store log entries in MongoDB with retry logic.

        Args:
            entries: List of log entries to store.

        Raises:
            Exception: If storing fails after all retries.
        """
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                # Create Log instances
                logs = [Log(**entry) for entry in entries]

                # Insert logs
                await Log.insert_many(logs)
                return

            except Exception as e:
                last_error = e
                retries += 1

                if retries < self.max_retries:
                    # Wait before retrying
                    await asyncio.sleep(self.retry_delay * (2 ** (retries - 1)))

        # If we get here, all retries failed
        if last_error:
            raise last_error
        raise Exception("Failed to store logs after all retries")

    async def emit(self, log_entry: Dict[str, Any]) -> None:
        """Store a log entry in MongoDB.

        Args:
            log_entry: The log entry to store.

        Raises:
            Exception: If storing fails after all retries.
        """
        await self._store_entries([log_entry])

    async def flush(self) -> None:
        """Flush buffered log entries to MongoDB."""
        if not self._batch:
            return

        await self._store_entries(self._batch)
        self._batch.clear()

    async def close(self) -> None:
        """Close the handler and flush any remaining entries."""
        await self.flush()
