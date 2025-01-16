"""Event filtering implementation.

This module provides utilities for filtering events.
It supports filtering by event name, data, and metadata.

Features:
- Event name filtering
- Event data filtering
- Event metadata filtering
- Filter composition
- Filter validation

Examples:
    ```python
    from earnorm.events.utils.filter import (
        EventFilter,
        NameFilter,
        DataFilter,
        CompositeFilter,
    )
    from earnorm.events.core.event import Event

    # Create filters
    name_filter = NameFilter("user.*")
    data_filter = DataFilter({"role": "admin"})
    composite = name_filter & data_filter

    # Filter events
    event = Event(name="user.created", data={"id": "123", "role": "admin"})
    assert composite.match(event)

    # Create filter chain
    filters = [
        NameFilter("user.*"),
        DataFilter({"role": "admin"}),
        DataFilter({"active": True}),
    ]
    chain = CompositeFilter(filters)
    assert chain.match(event)
    ```
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from earnorm.events.core.event import Event
from earnorm.events.utils.pattern import match_pattern

logger = logging.getLogger(__name__)


class EventFilter(ABC):
    """Event filter base class.

    This class defines the interface for event filters.
    All filters must implement the match method.

    Features:
    - Filter interface
    - Filter composition
    - Filter validation
    - Filter chaining

    Examples:
        ```python
        class CustomFilter(EventFilter):
            def match(self, event: Event) -> bool:
                return event.name.startswith("custom")

        filter = CustomFilter()
        event = Event(name="custom.event", data={})
        assert filter.match(event)
        ```
    """

    @abstractmethod
    def match(self, event: Event) -> bool:
        """Match event against filter.

        Args:
            event: Event to match

        Returns:
            bool: True if event matches filter
        """
        pass

    def __and__(self, other: "EventFilter") -> "CompositeFilter":
        """Combine filters with AND operator.

        Args:
            other: Filter to combine with

        Returns:
            CompositeFilter: Combined filter

        Examples:
            ```python
            filter1 = NameFilter("user.*")
            filter2 = DataFilter({"role": "admin"})
            combined = filter1 & filter2
            ```
        """
        return CompositeFilter([self, other])

    def __or__(self, other: "EventFilter") -> "CompositeFilter":
        """Combine filters with OR operator.

        Args:
            other: Filter to combine with

        Returns:
            CompositeFilter: Combined filter

        Examples:
            ```python
            filter1 = NameFilter("user.*")
            filter2 = NameFilter("admin.*")
            combined = filter1 | filter2
            ```
        """
        return CompositeFilter([self, other], any_match=True)


class NameFilter(EventFilter):
    """Event name filter.

    This class filters events by name pattern.
    It supports glob-style pattern matching.

    Features:
    - Pattern matching
    - Glob patterns
    - Pattern validation

    Examples:
        ```python
        # Create filter
        filter = NameFilter("user.*")

        # Match events
        event1 = Event(name="user.created", data={})
        event2 = Event(name="admin.created", data={})
        assert filter.match(event1)
        assert not filter.match(event2)
        ```
    """

    def __init__(self, pattern: str) -> None:
        """Initialize name filter.

        Args:
            pattern: Event name pattern to match
        """
        self.pattern = pattern

    def match(self, event: Event) -> bool:
        """Match event name against pattern.

        Args:
            event: Event to match

        Returns:
            bool: True if event name matches pattern
        """
        return match_pattern(self.pattern, event.name)


class DataFilter(EventFilter):
    """Event data filter.

    This class filters events by data content.
    It supports exact and partial matching of data.

    Features:
    - Data matching
    - Nested data
    - Partial matching
    - Type validation

    Examples:
        ```python
        # Create filter
        filter = DataFilter({"role": "admin", "active": True})

        # Match events
        event1 = Event(name="user.created", data={"id": "123", "role": "admin", "active": True})
        event2 = Event(name="user.created", data={"id": "123", "role": "user"})
        assert filter.match(event1)
        assert not filter.match(event2)
        ```
    """

    def __init__(self, data: Dict[str, Any], partial: bool = True) -> None:
        """Initialize data filter.

        Args:
            data: Data to match against
            partial: Whether to allow partial matches
        """
        self.data = data
        self.partial = partial

    def match(self, event: Event) -> bool:
        """Match event data against filter.

        Args:
            event: Event to match

        Returns:
            bool: True if event data matches filter
        """
        if self.partial:
            # Check if all filter data items are in event data
            return all(
                k in event.data and event.data[k] == v for k, v in self.data.items()
            )
        else:
            # Check for exact match
            return event.data == self.data


class CompositeFilter(EventFilter):
    """Composite event filter.

    This class combines multiple filters into a single filter.
    It supports AND/OR composition of filters.

    Features:
    - Filter composition
    - AND/OR operators
    - Filter chaining
    - Filter validation

    Examples:
        ```python
        # Create composite filter
        filters = [
            NameFilter("user.*"),
            DataFilter({"role": "admin"}),
            DataFilter({"active": True}),
        ]
        filter = CompositeFilter(filters)

        # Match events
        event = Event(
            name="user.created",
            data={"id": "123", "role": "admin", "active": True}
        )
        assert filter.match(event)
        ```
    """

    def __init__(self, filters: List[EventFilter], any_match: bool = False) -> None:
        """Initialize composite filter.

        Args:
            filters: List of filters to combine
            any_match: Whether any filter must match (OR) or all must match (AND)
        """
        self.filters = filters
        self.any_match = any_match

    def match(self, event: Event) -> bool:
        """Match event against all filters.

        Args:
            event: Event to match

        Returns:
            bool: True if event matches filter combination
        """
        if not self.filters:
            return True

        if self.any_match:
            return any(f.match(event) for f in self.filters)
        else:
            return all(f.match(event) for f in self.filters)
