"""File handler for writing logs to files."""

import logging
import os
from typing import Any, Dict, List, Optional, TextIO, cast

from .base import BaseHandler

logger = logging.getLogger(__name__)


class FileHandler(BaseHandler):
    """Handler for writing logs to files.

    This handler writes log entries to a file with support for:
    - Custom file paths and modes
    - File permissions
    - Directory creation
    - File buffering

    Examples:
        >>> # Basic usage
        >>> handler = FileHandler('app.log')
        >>> await handler.emit({'message': 'test'})

        >>> # With custom mode and permissions
        >>> handler = FileHandler(
        ...     filename='app.log',
        ...     mode='a',
        ...     encoding='utf-8',
        ...     permissions=0o644
        ... )
        >>> await handler.emit({'message': 'test'})

        >>> # With batching
        >>> handler = FileHandler(
        ...     filename='app.log',
        ...     batch_size=100
        ... )
        >>> for i in range(50):
        ...     await handler.handle({'message': f'message {i}'})
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        encoding: str = "utf-8",
        permissions: Optional[int] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """Initialize the file handler.

        Args:
            filename: Path to the log file.
            mode: File open mode ('a' for append, 'w' for write).
            encoding: File encoding.
            permissions: File permissions (e.g. 0o644).
            batch_size: Optional batch size for batching log entries.

        Raises:
            OSError: If there is an error creating directories or setting permissions.
            ValueError: If the mode or encoding is invalid.
        """
        super().__init__(batch_size=batch_size or 100)
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.permissions = permissions
        self._file: Optional[TextIO] = None
        self._batch: List[Dict[str, Any]] = []

        try:
            # Create directory if needed
            directory = os.path.dirname(filename)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Set file permissions if specified
            if permissions is not None and os.path.exists(filename):
                os.chmod(filename, permissions)
        except OSError as e:
            logger.exception("Error initializing file handler: %s", e)
            raise

    def _ensure_file_open(self) -> None:
        """Ensure the file is open for writing.

        Raises:
            OSError: If there is an error opening the file or setting permissions.
            ValueError: If the mode or encoding is invalid.
        """
        try:
            if self._file is None or self._file.closed:
                file = open(self.filename, mode=self.mode, encoding=self.encoding)
                self._file = cast(TextIO, file)

                # Set permissions on new file
                if self.permissions is not None:
                    os.chmod(self.filename, self.permissions)
        except (OSError, ValueError) as e:
            logger.exception("Error opening log file: %s", e)
            raise

    async def emit(self, log_entry: Dict[str, Any]) -> None:
        """Write a log entry to the file.

        Args:
            log_entry: The log entry to write.

        Raises:
            OSError: If there is an error writing to the file.
            ValueError: If the log entry cannot be formatted.
        """
        try:
            self._ensure_file_open()

            # Format log entry as string
            log_line = f"{log_entry.get('timestamp', '')} [{log_entry.get('level', 'INFO')}] {log_entry.get('message', '')}\n"

            # Write to file
            if self._file is not None:
                self._file.write(log_line)
                self._file.flush()
        except (OSError, ValueError) as e:
            logger.exception("Error writing log entry: %s", e)
            raise

    async def flush(self) -> None:
        """Flush buffered log entries to file.

        Raises:
            OSError: If there is an error writing to the file.
            ValueError: If a log entry cannot be formatted.
        """
        if not self._batch:
            return

        try:
            self._ensure_file_open()

            # Write all entries
            for entry in self._batch:
                await self.emit(entry)

            self._batch.clear()
        except (OSError, ValueError) as e:
            logger.exception("Error flushing log entries: %s", e)
            raise

    async def close(self) -> None:
        """Close the handler and the file.

        Raises:
            OSError: If there is an error closing the file.
        """
        try:
            await self.flush()

            if self._file is not None:
                self._file.close()
                self._file = None
        except OSError as e:
            logger.exception("Error closing file handler: %s", e)
            raise
