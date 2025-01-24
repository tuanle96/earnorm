"""Masking processor for masking sensitive data in log entries."""

import re
from typing import Any, Dict, List, Optional, Pattern, TypeVar, Union, cast

from .base import BaseProcessor

T = TypeVar("T")


class MaskingProcessor(BaseProcessor):
    """Processor for masking sensitive data in log entries.

    This processor masks sensitive data in log entries based on:
    - Field names (e.g. 'password', 'credit_card')
    - Patterns (e.g. credit card numbers, emails)

    Examples:
        >>> # Mask specific fields
        >>> processor = MaskingProcessor(
        ...     fields=['password', 'credit_card'],
        ...     mask='***'
        ... )
        >>> log_entry = {'password': '123456', 'message': 'test'}
        >>> processed = processor.process(log_entry)
        >>> assert processed['password'] == '***'

        >>> # Mask using patterns
        >>> processor = MaskingProcessor(
        ...     patterns=[r'[0-9]{16}'],  # Credit card numbers
        ...     mask='****-****-****-****'
        ... )
        >>> log_entry = {'message': 'Card: 1234567890123456'}
        >>> processed = processor.process(log_entry)
        >>> assert 'Card: ****-****-****-****' in processed['message']

        >>> # Mask nested fields
        >>> processor = MaskingProcessor(
        ...     fields=['password'],
        ...     mask='***'
        ... )
        >>> log_entry = {
        ...     'user': {
        ...         'password': '123456',
        ...         'name': 'test'
        ...     }
        ... }
        >>> processed = processor.process(log_entry)
        >>> assert processed['user']['password'] == '***'
    """

    def __init__(
        self,
        fields: Optional[List[str]] = None,
        patterns: Optional[List[Union[str, Pattern[str]]]] = None,
        mask: str = "***",
        recursive: bool = True,
    ):
        """Initialize the masking processor.

        Args:
            fields: List of field names to mask.
            patterns: List of regex patterns to mask. Can be strings or
                compiled regex patterns.
            mask: String to use as mask.
            recursive: Whether to mask nested dictionaries.
        """
        self.fields = set(fields or [])
        self.patterns = [
            re.compile(p) if isinstance(p, str) else p for p in (patterns or [])
        ]
        self.mask = mask
        self.recursive = recursive

    def _mask_patterns(self, value: str) -> str:
        """Mask all patterns in a string value."""
        result = value
        for pattern in self.patterns:
            result = pattern.sub(self.mask, result)
        return result

    def _mask_value(self, value: Any) -> Any:
        """Mask a single value."""
        if isinstance(value, str):
            return self._mask_patterns(value)
        elif isinstance(value, dict):
            value_dict = cast(Dict[str, Any], value)
            if self.recursive:
                return self._mask_dict(value_dict)
            return value_dict
        elif isinstance(value, list):
            value_list = cast(List[Any], value)
            if self.recursive:
                return [self._mask_value(item) for item in value_list]
            return value_list
        return value

    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask values in a dictionary."""
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if key in self.fields:
                result[key] = self.mask
            else:
                result[key] = self._mask_value(value)
        return result

    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry and mask sensitive data.

        Args:
            log_entry: The log entry to process.

        Returns:
            Dict[str, Any]: The processed log entry with masked values.
        """
        return self._mask_dict(log_entry)
