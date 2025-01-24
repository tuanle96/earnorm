"""Base processor for log entries."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseProcessor(ABC):
    """Base class for all log processors.

    This class defines the interface that all log processors must implement.
    Log processors are responsible for processing log entries before they are
    passed to handlers.

    Examples:
        >>> class MyProcessor(BaseProcessor):
        ...     def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        ...         # Add custom field
        ...         log_entry['custom_field'] = 'custom_value'
        ...         return log_entry
        ...
        >>> processor = MyProcessor()
        >>> log_entry = {'message': 'test'}
        >>> processed = processor.process(log_entry)
        >>> assert processed['custom_field'] == 'custom_value'
    """

    @abstractmethod
    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry.

        Args:
            log_entry: The log entry to process.

        Returns:
            The processed log entry.
        """
        pass
