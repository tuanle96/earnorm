"""Base handler class for log handlers."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for log handlers.

    This class defines the interface that all log handlers must implement.
    It provides basic functionality for batching log entries before sending
    them to their destinations.

    Examples:
        >>> class CustomHandler(BaseHandler):
        ...     async def emit(self, log_entry):
        ...         print(log_entry)
        ...     async def flush(self):
        ...         pass
        ...     async def close(self):
        ...         pass
        >>> handler = CustomHandler(batch_size=2)
        >>> await handler.handle({'message': 'test'})
    """

    def __init__(self, batch_size: Optional[int] = None) -> None:
        """Initialize the handler.

        Args:
            batch_size: Optional batch size for batching log entries.
                If None, entries are processed immediately.
                If > 0, entries are batched until the batch size is reached.

        Raises:
            ValueError: If batch_size is less than 0.
        """
        if batch_size is not None and batch_size < 0:
            raise ValueError("batch_size must be >= 0")

        self.batch_size = batch_size
        self._batch: List[Dict[str, Any]] = []

    async def handle(self, log_entry: Dict[str, Any]) -> None:
        """Handle a log entry.

        If batching is enabled, the entry is added to the batch.
        When the batch is full, all entries are flushed.
        If batching is disabled, the entry is emitted immediately.

        Args:
            log_entry: The log entry to handle.

        Raises:
            Exception: If there is an error handling the log entry.
        """
        try:
            if not self.batch_size:
                await self.emit(log_entry)
                return

            self._batch.append(log_entry)
            if len(self._batch) >= self.batch_size:
                await self.flush()
        except Exception as e:
            logger.exception("Error handling log entry: %s", e)
            raise

    async def emit(self, log_entry: Dict[str, Any]) -> None:
        """Emit a log entry.

        This method must be implemented by subclasses to define how
        log entries are emitted to their destination.

        Args:
            log_entry: The log entry to emit.

        Raises:
            NotImplementedError: If the method is not implemented.
            Exception: If there is an error emitting the log entry.
        """
        raise NotImplementedError

    async def flush(self) -> None:
        """Flush any buffered log entries.

        This method must be implemented by subclasses to define how
        buffered entries are flushed to their destination.

        Raises:
            NotImplementedError: If the method is not implemented.
            Exception: If there is an error flushing the entries.
        """
        raise NotImplementedError

    async def close(self) -> None:
        """Close the handler and clean up any resources.

        This method must be implemented by subclasses to define how
        the handler is closed and resources are cleaned up.

        Raises:
            NotImplementedError: If the method is not implemented.
            Exception: If there is an error closing the handler.
        """
        raise NotImplementedError
