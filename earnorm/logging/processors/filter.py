"""Filter processor for filtering log entries based on conditions."""

import re
from typing import Any, Callable, Dict, List, Optional

from .base import BaseProcessor


class FilterProcessor(BaseProcessor):
    """Processor for filtering log entries based on conditions.

    This processor can filter log entries based on:
    - Minimum log level
    - Include/exclude patterns for messages
    - Custom filter functions

    Examples:
        >>> # Filter by minimum level
        >>> processor = FilterProcessor(min_level='WARNING')
        >>> log_entry = {'level': 'INFO', 'message': 'test'}
        >>> assert processor.process(log_entry) == {}  # Filtered out
        >>> log_entry = {'level': 'ERROR', 'message': 'test'}
        >>> assert processor.process(log_entry) == log_entry  # Passed through

        >>> # Filter by patterns
        >>> processor = FilterProcessor(
        ...     include_patterns=[r'important.*'],
        ...     exclude_patterns=[r'debug.*']
        ... )
        >>> log_entry = {'message': 'debug info'}
        >>> assert processor.process(log_entry) == {}  # Filtered out
        >>> log_entry = {'message': 'important error'}
        >>> assert processor.process(log_entry) == log_entry  # Passed through

        >>> # Filter by custom function
        >>> def custom_filter(entry):
        ...     return entry.get('user_id') == 'admin'
        >>> processor = FilterProcessor(custom_filter=custom_filter)
        >>> log_entry = {'user_id': 'user'}
        >>> assert processor.process(log_entry) == {}  # Filtered out
        >>> log_entry = {'user_id': 'admin'}
        >>> assert processor.process(log_entry) == log_entry  # Passed through
    """

    # Log level hierarchy
    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}

    def __init__(
        self,
        min_level: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        custom_filter: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        """Initialize the filter processor.

        Args:
            min_level: Minimum log level to include (e.g. 'WARNING').
            include_patterns: List of regex patterns that messages must match.
            exclude_patterns: List of regex patterns that messages must not match.
            custom_filter: Custom function that takes a log entry and returns
                True if the entry should be included.
        """
        self.min_level = min_level
        self.include_patterns = [
            re.compile(pattern) for pattern in (include_patterns or [])
        ]
        self.exclude_patterns = [
            re.compile(pattern) for pattern in (exclude_patterns or [])
        ]
        self.custom_filter = custom_filter

    def _check_level(self, log_entry: Dict[str, Any]) -> bool:
        """Check if the log entry meets the minimum level requirement."""
        if not self.min_level:
            return True

        entry_level = log_entry.get("level", "INFO")
        min_level_value = self.LEVELS.get(self.min_level, 0)
        entry_level_value = self.LEVELS.get(entry_level, 0)

        return entry_level_value >= min_level_value

    def _check_patterns(self, log_entry: Dict[str, Any]) -> bool:
        """Check if the log entry matches the include/exclude patterns."""
        message = log_entry.get("message", "")

        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if pattern.search(message):
                return False

        # If no include patterns, accept all non-excluded messages
        if not self.include_patterns:
            return True

        # Check include patterns
        for pattern in self.include_patterns:
            if pattern.search(message):
                return True

        return False

    def _check_custom_filter(self, log_entry: Dict[str, Any]) -> bool:
        """Check if the log entry passes the custom filter."""
        if not self.custom_filter:
            return True

        return self.custom_filter(log_entry)

    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry by applying filters.

        Args:
            log_entry: The log entry to process.

        Returns:
            The log entry if it passes all filters, empty dict otherwise.
        """
        # Apply all filters
        if not self._check_level(log_entry):
            return {}

        if not self._check_patterns(log_entry):
            return {}

        if not self._check_custom_filter(log_entry):
            return {}

        return log_entry
