"""Base handler for logging.

This module provides the base handler class that all log handlers must inherit from.
It defines the interface for handling log entries.

    Examples:
        >>> class CustomHandler(BaseHandler):
    ...     async def handle(self, log_entry: Dict[str, Any]) -> None:
    ...         # Custom handling logic
    ...         print(f"[{log_entry['level']}] {log_entry['message']}")
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseHandler(ABC):
    """Base class for all log handlers.

    This class defines the interface that all handlers must implement.
    Handlers are responsible for processing and storing log entries.

    Attributes:
        batch_size: Number of logs to process in a batch
        format_string: Format string for log messages
    """

    def __init__(
        self, batch_size: int = 1, format_string: Optional[str] = None
    ) -> None:
        """Initialize the handler.

        Args:
            batch_size: Number of logs to process in a batch
            format_string: Format string for log messages
        """
        self.batch_size = batch_size
        self.format_string = format_string or "[{level}] {message}"
        self._batch: list[Dict[str, Any]] = []

    @abstractmethod
    async def handle(self, log_entry: Dict[str, Any]) -> None:
        """Handle a log entry.

        This method must be implemented by all handlers.
        It should process and store the log entry.

        Args:
            log_entry: Log entry to handle
        """
        raise NotImplementedError

    async def flush(self) -> None:
        """Flush any buffered log entries.

        This method should be called to ensure all logs are processed.
        """
        if self._batch:
            await self._flush_batch()
            self._batch.clear()

    async def _flush_batch(self) -> None:
        """Flush the current batch of log entries.

        This method should be implemented by handlers that support batching.
        """
        pass

    def format(self, log_entry: Dict[str, Any]) -> str:
        """Format a log entry using the format string.

        Args:
            log_entry: Log entry to format

        Returns:
            Formatted log message
        """
        try:
            return self.format_string.format(**log_entry)
        except KeyError as e:
            return f"[ERROR] Invalid format string: {e}"

    async def close(self) -> None:
        """Close the handler and clean up resources.

        This method should be called when the handler is no longer needed.
        """
        await self.flush()
