"""Event pattern matching implementation.

This module provides utilities for event pattern matching.
It supports glob-style patterns with wildcards and path segments.

Features:
- Glob-style pattern matching
- Path segment matching
- Pattern validation
- Pattern compilation
- Pattern caching

Examples:
    ```python
    from earnorm.events.utils.pattern import match_pattern, compile_pattern

    # Simple pattern matching
    assert match_pattern("user.created", "user.created")
    assert match_pattern("user.*", "user.created")
    assert match_pattern("*.created", "user.created")
    assert not match_pattern("user.updated", "user.created")

    # Compile pattern for reuse
    pattern = compile_pattern("user.*.completed")
    assert pattern.match("user.task.completed")
    assert pattern.match("user.job.completed")
    assert not pattern.match("user.task.started")
    ```
"""

import fnmatch
import logging
import re
from typing import Dict, Pattern

logger = logging.getLogger(__name__)


class EventPattern:
    """Event pattern.

    This class represents a compiled event pattern.
    It provides methods for matching event names against the pattern.

    Features:
    - Pattern compilation
    - Fast matching
    - Pattern validation
    - Pattern caching

    Attributes:
        pattern: Original pattern string
        regex: Compiled regex pattern
    """

    def __init__(self, pattern: str) -> None:
        """Initialize event pattern.

        Args:
            pattern: Pattern string to compile

        Examples:
            ```python
            # Create pattern
            pattern = EventPattern("user.*.completed")

            # Match event names
            assert pattern.match("user.task.completed")
            assert not pattern.match("user.task.started")
            ```
        """
        self.pattern = pattern
        self.regex = self._compile_pattern(pattern)

    def match(self, event_name: str) -> bool:
        """Match event name against pattern.

        This method checks if an event name matches the pattern.

        Args:
            event_name: Event name to match

        Returns:
            bool: True if event name matches pattern

        Examples:
            ```python
            pattern = EventPattern("user.*.completed")

            # Match event names
            assert pattern.match("user.task.completed")
            assert pattern.match("user.job.completed")
            assert not pattern.match("user.task.started")
            ```
        """
        return bool(self.regex.match(event_name))

    def _compile_pattern(self, pattern: str) -> Pattern[str]:
        """Compile pattern to regex.

        This method converts a glob pattern to a regex pattern.

        Args:
            pattern: Pattern to compile

        Returns:
            Pattern: Compiled regex pattern

        Examples:
            ```python
            pattern = EventPattern("user.*.completed")
            regex = pattern._compile_pattern("user.*.completed")
            assert regex.match("user.task.completed")
            ```
        """
        # Escape special characters
        regex = re.escape(pattern)

        # Convert glob patterns to regex
        regex = regex.replace(r"\*", r"[^.]+")
        regex = regex.replace(r"\?", r".")

        # Anchor pattern
        regex = f"^{regex}$"

        # Compile regex
        return re.compile(regex)

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            str: Pattern string
        """
        return self.pattern

    def __repr__(self) -> str:
        """Get string representation.

        Returns:
            str: Pattern string
        """
        return f"EventPattern({self.pattern!r})"


# Pattern cache
_pattern_cache: Dict[str, EventPattern] = {}


def compile_pattern(pattern: str) -> EventPattern:
    """Compile event pattern.

    This function compiles a pattern string into an EventPattern.
    It caches compiled patterns for reuse.

    Args:
        pattern: Pattern string to compile

    Returns:
        EventPattern: Compiled pattern

    Examples:
        ```python
        # Compile pattern
        pattern = compile_pattern("user.*.completed")

        # Match event names
        assert pattern.match("user.task.completed")
        assert pattern.match("user.job.completed")
        assert not pattern.match("user.task.started")
        ```
    """
    # Check cache
    if pattern in _pattern_cache:
        return _pattern_cache[pattern]

    # Compile pattern
    compiled = EventPattern(pattern)
    _pattern_cache[pattern] = compiled
    return compiled


def match_pattern(pattern: str, event_name: str) -> bool:
    """Match event name against pattern.

    This function checks if an event name matches a pattern.
    It uses glob-style pattern matching.

    Args:
        pattern: Pattern to match against
        event_name: Event name to match

    Returns:
        bool: True if event name matches pattern

    Examples:
        ```python
        # Simple pattern matching
        assert match_pattern("user.created", "user.created")
        assert match_pattern("user.*", "user.created")
        assert match_pattern("*.created", "user.created")
        assert not match_pattern("user.updated", "user.created")

        # Complex patterns
        assert match_pattern("user.*.completed", "user.task.completed")
        assert match_pattern("*.*.deleted", "user.task.deleted")
        ```
    """
    return fnmatch.fnmatch(event_name, pattern)
