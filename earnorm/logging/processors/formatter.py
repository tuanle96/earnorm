"""Formatter processor for formatting log entries."""

import traceback
from typing import Any, Dict, Optional

from .base import BaseProcessor


class FormatterProcessor(BaseProcessor):
    """Processor for formatting log entries.

    This processor formats log entries by:
    - Adding stack traces for errors
    - Formatting error messages
    - Adding source code information
    - Formatting timestamps

    Examples:
        >>> # Format error with stack trace
        >>> processor = FormatterProcessor()
        >>> try:
        ...     raise ValueError('test error')
        ... except Exception as e:
        ...     log_entry = {
        ...         'level': 'ERROR',
        ...         'message': str(e),
        ...         'error': e
        ...     }
        >>> processed = processor.process(log_entry)
        >>> assert 'stack_trace' in processed
        >>> assert 'error_type' in processed
        >>> assert processed['error_type'] == 'ValueError'

        >>> # Format regular message
        >>> log_entry = {
        ...     'level': 'INFO',
        ...     'message': 'test message',
        ...     'module': 'test_module',
        ...     'line': 42
        ... }
        >>> processed = processor.process(log_entry)
        >>> assert processed['source'] == 'test_module:42'
    """

    def __init__(self, max_trace_length: Optional[int] = None):
        """Initialize the formatter processor.

        Args:
            max_trace_length: Maximum number of stack trace lines to include.
                If None, includes entire stack trace.
        """
        self.max_trace_length = max_trace_length

    def _format_error(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format error information in the log entry."""
        error = log_entry.get("error")
        if not error or not isinstance(error, Exception):
            return log_entry

        # Add error type
        log_entry["error_type"] = error.__class__.__name__

        # Add stack trace
        stack_trace = traceback.format_exception(
            type(error), error, error.__traceback__
        )

        if self.max_trace_length:
            stack_trace = stack_trace[: self.max_trace_length]

        log_entry["stack_trace"] = "".join(stack_trace)

        # Remove error object as it's not JSON serializable
        del log_entry["error"]

        return log_entry

    def _format_source(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format source code information in the log entry."""
        module = log_entry.get("module")
        line = log_entry.get("line")

        if module and line:
            log_entry["source"] = f"{module}:{line}"

        return log_entry

    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry by formatting its contents.

        Args:
            log_entry: The log entry to process.

        Returns:
            The formatted log entry.
        """
        # Format error information if present
        log_entry = self._format_error(log_entry)

        # Format source code information if present
        log_entry = self._format_source(log_entry)

        return log_entry
