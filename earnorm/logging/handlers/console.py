"""Console handler for outputting logs to console."""

import logging
import sys
from typing import Any, Dict, List, Optional

from .base import BaseHandler

logger = logging.getLogger(__name__)


class ConsoleHandler(BaseHandler):
    """Handler for outputting logs to console.

    This handler formats and prints log entries to the console (stdout/stderr).
    Error logs (ERROR, CRITICAL) are printed to stderr, while other logs are
    printed to stdout.

    Examples:
        >>> # Basic usage with default format
        >>> handler = ConsoleHandler()
        >>> log_entry = {
        ...     'level': 'INFO',
        ...     'message': 'test message',
        ...     'module': 'test_module'
        ... }
        >>> await handler.emit(log_entry)  # Prints: [INFO] test message

        >>> # Custom format
        >>> handler = ConsoleHandler(
        ...     format_string='[{level}] {module}: {message}'
        ... )
        >>> await handler.emit(log_entry)  # Prints: [INFO] test_module: test message

        >>> # Batch output
        >>> handler = ConsoleHandler(batch_size=2)
        >>> await handler.handle({'level': 'INFO', 'message': 'first'})
        >>> await handler.handle({'level': 'INFO', 'message': 'second'})
        >>> # Prints both messages when batch size is reached
    """

    # Log levels that should go to stderr
    ERROR_LEVELS = {"ERROR", "CRITICAL"}

    def __init__(
        self,
        format_string: Optional[str] = None,
        batch_size: Optional[int] = None,
        color: bool = True,
    ) -> None:
        """Initialize the console handler.

        Args:
            format_string: Optional format string for log messages.
                Default: '[{level}] {message}'
            batch_size: Optional batch size for batching log entries.
                If None, entries are printed immediately.
            color: Whether to colorize output based on log level.

        Raises:
            ValueError: If batch_size is negative.
        """
        super().__init__(batch_size)
        self.format_string = format_string or "[{level}] {message}"
        self.color = color
        self._batch: List[Dict[str, Any]] = []

    def _get_color_code(self, level: str) -> str:
        """Get ANSI color code for log level.

        Args:
            level: The log level to get the color code for.

        Returns:
            The ANSI color code for the log level, or an empty string
            if color is disabled.
        """
        if not self.color:
            return ""

        return {
            "DEBUG": "\033[36m",  # Cyan
            "INFO": "\033[32m",  # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",  # Red
            "CRITICAL": "\033[35m",  # Magenta
        }.get(level, "")

    def _format_entry(self, log_entry: Dict[str, Any]) -> str:
        """Format a log entry for console output.

        Args:
            log_entry: The log entry to format.

        Returns:
            The formatted log entry string.

        Raises:
            KeyError: If a required field is missing from the log entry.
            ValueError: If the format string is invalid.
        """
        try:
            # Get color code if enabled
            color_code = self._get_color_code(log_entry.get("level", "INFO"))
            reset_code = "\033[0m" if color_code else ""

            # Format message
            message = self.format_string.format(**log_entry)

            return f"{color_code}{message}{reset_code}"
        except (KeyError, ValueError) as e:
            logger.exception("Error formatting log entry: %s", e)
            raise

    async def emit(self, log_entry: Dict[str, Any]) -> None:
        """Print a log entry to the console.

        Args:
            log_entry: The log entry to print.

        Raises:
            KeyError: If a required field is missing from the log entry.
            ValueError: If the format string is invalid.
            OSError: If there is an error writing to stdout/stderr.
        """
        try:
            # Format the entry
            formatted = self._format_entry(log_entry)

            # Choose output stream based on level
            stream = (
                sys.stderr
                if log_entry.get("level") in self.ERROR_LEVELS
                else sys.stdout
            )

            # Print and flush
            print(formatted, file=stream, flush=True)
        except Exception as e:
            logger.exception("Error emitting log entry: %s", e)
            raise

    async def flush(self) -> None:
        """Flush buffered log entries to console.

        Raises:
            KeyError: If a required field is missing from a log entry.
            ValueError: If the format string is invalid.
            OSError: If there is an error writing to stdout/stderr.
        """
        try:
            for entry in self._batch:
                await self.emit(entry)

            self._batch.clear()
        except Exception as e:
            logger.exception("Error flushing log entries: %s", e)
            raise

    async def close(self) -> None:
        """Close the handler and flush any remaining entries.

        Raises:
            KeyError: If a required field is missing from a log entry.
            ValueError: If the format string is invalid.
            OSError: If there is an error writing to stdout/stderr.
        """
        try:
            await self.flush()
        except Exception as e:
            logger.exception("Error closing console handler: %s", e)
            raise
