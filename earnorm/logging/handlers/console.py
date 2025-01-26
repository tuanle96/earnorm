"""Console handler for logging.

This module provides a handler for printing logs to the console with
color support and customizable formatting.

Examples:
    >>> handler = ConsoleHandler(
    ...     format_string="[{level}] {message}",
    ...     use_colors=True
    ... )
    >>> await handler.handle({
    ...     'level': 'INFO',
    ...     'message': 'Test message'
    ... })
    [INFO] Test message
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from .base import BaseHandler

logger = logging.getLogger(__name__)

# ANSI color codes
COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",  # Reset
}


class ConsoleHandler(BaseHandler):
    """Handler for printing logs to the console.

    This handler supports:
    - Color output for different log levels
    - Customizable format strings
    - Batch processing of logs

    Attributes:
        use_colors: Whether to use ANSI colors
        stream: Output stream (stdout or stderr)
    """

    def __init__(
        self,
        batch_size: int = 1,
        format_string: Optional[str] = None,
        use_colors: bool = True,
        stream: Any = sys.stdout,
    ) -> None:
        """Initialize the console handler.

        Args:
            batch_size: Number of logs to process in a batch
            format_string: Format string for log messages
            use_colors: Whether to use ANSI colors
            stream: Output stream (defaults to stdout)
        """
        super().__init__(batch_size, format_string)
        self.use_colors = use_colors
        self.stream = stream
        self._batch: List[Dict[str, Any]] = []

    def _get_color_code(self, level: str) -> str:
        """Get ANSI color code for log level.

        Args:
            level: The log level to get the color code for.

        Returns:
            The ANSI color code for the log level, or an empty string
            if color is disabled.
        """
        if not self.use_colors:
            return ""

        return COLORS.get(level, COLORS["RESET"])

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

            # Format message
            message = self.format_string.format(**log_entry)

            return f"{color_code}{message}{COLORS['RESET']}"
        except (KeyError, ValueError) as e:
            logger.exception("Error formatting log entry: %s", e)
            raise

    async def handle(self, log_entry: Dict[str, Any]) -> None:
        """Handle a log entry by printing it to the console.

        Args:
            log_entry: Log entry to handle
        """
        self._batch.append(log_entry)
        if len(self._batch) >= self.batch_size:
            await self.flush()

    async def _flush_batch(self) -> None:
        """Flush the current batch of log entries."""
        for entry in self._batch:
            message = self._format_entry(entry)
            print(message, file=self.stream, flush=True)

    async def close(self) -> None:
        """Close the handler and flush any remaining logs."""
        await self.flush()
        if hasattr(self.stream, "flush"):
            self.stream.flush()
