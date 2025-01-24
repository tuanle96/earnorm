"""Sampling processor for sampling log entries."""

import random
from typing import Any, Callable, Dict, List, Optional

from .base import BaseProcessor


class SamplingProcessor(BaseProcessor):
    """Processor for sampling log entries.

    This processor samples log entries based on:
    - Sample rate (0.0 to 1.0)
    - Sampling rules (e.g. always sample errors)

    Examples:
        >>> # Sample 10% of logs
        >>> processor = SamplingProcessor(sample_rate=0.1)
        >>> log_entry = {'level': 'info', 'message': 'test'}
        >>> sampled = processor.process(log_entry)
        >>> if sampled:
        ...     print('Log entry was sampled')

        >>> # Always sample errors
        >>> processor = SamplingProcessor(
        ...     sample_rate=0.1,
        ...     always_sample={'level': ['error', 'critical']}
        ... )
        >>> log_entry = {'level': 'error', 'message': 'test'}
        >>> sampled = processor.process(log_entry)  # Always True

        >>> # Sample based on custom rules
        >>> def custom_rule(log_entry):
        ...     return log_entry.get('user_id') == '123'
        >>> processor = SamplingProcessor(
        ...     sample_rate=0.1,
        ...     sampling_rules=[custom_rule]
        ... )
        >>> log_entry = {'user_id': '123', 'message': 'test'}
        >>> sampled = processor.process(log_entry)  # Always True
    """

    def __init__(
        self,
        sample_rate: float = 1.0,
        always_sample: Optional[Dict[str, List[str]]] = None,
        sampling_rules: Optional[List[Callable[[Dict[str, Any]], bool]]] = None,
    ):
        """Initialize the sampling processor.

        Args:
            sample_rate: Rate at which to sample logs (0.0 to 1.0).
                1.0 means sample everything, 0.0 means sample nothing.
            always_sample: Dict mapping field names to lists of values that
                should always be sampled. For example:
                {'level': ['error', 'critical']}
            sampling_rules: List of functions that take a log entry and
                return True if it should be sampled. For example:
                [lambda x: x.get('user_id') == '123']
        """
        if not 0.0 <= sample_rate <= 1.0:
            raise ValueError("Sample rate must be between 0.0 and 1.0")

        self.sample_rate = sample_rate
        self.always_sample = always_sample or {}
        self.sampling_rules = sampling_rules or []

    def _should_always_sample(self, log_entry: Dict[str, Any]) -> bool:
        """Check if the log entry should always be sampled."""
        for field, values in self.always_sample.items():
            if field in log_entry and log_entry[field] in values:
                return True
        return False

    def _matches_sampling_rules(self, log_entry: Dict[str, Any]) -> bool:
        """Check if the log entry matches any sampling rules."""
        for rule in self.sampling_rules:
            if rule(log_entry):
                return True
        return False

    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry and decide if it should be sampled.

        Args:
            log_entry: The log entry to process.

        Returns:
            Dict[str, Any]: The log entry if it should be sampled,
                empty dict otherwise.
        """
        # Always sample if matches rules
        if self._should_always_sample(log_entry):
            return log_entry

        if self._matches_sampling_rules(log_entry):
            return log_entry

        # Random sampling based on rate
        if random.random() < self.sample_rate:
            return log_entry

        return {}
