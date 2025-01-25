"""Test utilities implementation.

This module provides utilities for testing event systems.
It includes mock backends, test event bus, and test helpers.

Features:
- Mock event backend
- Test event bus
- Event assertions
- Event recording
- Event replay

Examples:
    ```python
    from earnorm.events.utils.testing import MockBackend, TestEventBus, EventRecorder
    from earnorm.events.core.event import Event

    # Create mock backend
    backend = MockBackend()
    await backend.connect()

    # Create test bus
    bus = TestEventBus(backend)
    await bus.init()

    # Record events
    recorder = EventRecorder()
    await bus.subscribe("user.*", recorder)

    # Publish events
    event = Event(name="user.created", data={"id": "123"})
    await bus.publish(event)

    # Assert events
    assert recorder.has_event("user.created")
    assert recorder.count("user.*") == 1
    assert recorder.last_event.name == "user.created"
    ```
"""

import logging
from typing import Any, Dict, List, Optional, Set

from earnorm.di.lifecycle import LifecycleAware
from earnorm.events.backends.base import EventBackend
from earnorm.events.core.bus import EventBus
from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler
from earnorm.events.utils.pattern import match_pattern

logger = logging.getLogger(__name__)


class MockBackend(EventBackend):
    """Mock event backend.

    This class implements a mock event backend for testing.
    It stores events in memory and supports pattern matching.

    Features:
    - In-memory event storage
    - Pattern matching
    - Event replay
    - Connection simulation

    Examples:
        ```python
        # Create backend
        backend = MockBackend()
        await backend.connect()

        # Publish events
        event = Event(name="user.created", data={"id": "123"})
        await backend.publish(event)

        # Get events
        event = await backend.get()
        assert event.name == "user.created"
        ```
    """

    def __init__(self) -> None:
        """Initialize mock backend."""
        self._events: List[Event] = []
        self._subscriptions: Set[str] = set()
        self._connected = False

    @property
    def id(self) -> Optional[str]:
        """Get backend ID.

        Returns:
            str: Always returns "mock"
        """
        return "mock"

    @property
    def data(self) -> Dict[str, int]:
        """Get backend data.

        Returns:
            Dict containing backend state:
            - events: Number of stored events
            - subscriptions: Number of subscriptions
        """
        return {
            "events": len(self._events),
            "subscriptions": len(self._subscriptions),
        }

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            bool: True if backend is connected
        """
        return self._connected

    async def connect(self) -> None:
        """Connect to backend.

        This method simulates connecting to a backend.
        """
        self._connected = True
        logger.debug("Connected to mock backend")

    async def disconnect(self) -> None:
        """Disconnect from backend.

        This method simulates disconnecting from a backend.
        """
        self._connected = False
        self._events.clear()
        self._subscriptions.clear()
        logger.debug("Disconnected from mock backend")

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method adds an event to the in-memory store.

        Args:
            event: Event to publish
        """
        # Check subscriptions
        if not any(
            match_pattern(pattern, event.name) for pattern in self._subscriptions
        ):
            return

        # Store event
        self._events.append(event)
        logger.debug(f"Published event {event.name}")

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events.

        This method adds a subscription pattern.

        Args:
            pattern: Event pattern to match
        """
        self._subscriptions.add(pattern)
        logger.debug(f"Subscribed to pattern {pattern}")

    async def get(self) -> Optional[Event]:
        """Get next event.

        This method gets and removes the next event from the store.

        Returns:
            Optional[Event]: Next event if available
        """
        if not self._events:
            return None

        return self._events.pop(0)


class TestEventBus(EventBus):
    """Test event bus.

    This class extends EventBus with testing utilities.
    It provides methods for event assertions and recording.

    Features:
    - Event assertions
    - Event recording
    - Event replay
    - Handler tracking

    Examples:
        ```python
        # Create bus
        bus = TestEventBus(MockBackend())
        await bus.init()

        # Publish events
        event = Event(name="user.created", data={"id": "123"})
        await bus.publish(event)

        # Assert events
        assert bus.has_published("user.created")
        assert bus.published_count("user.*") == 1
        ```
    """

    def __init__(self, backend: EventBackend) -> None:
        """Initialize test bus.

        Args:
            backend: Event backend to use
        """
        super().__init__(backend)
        self._published: List[Event] = []

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method publishes an event and records it.

        Args:
            event: Event to publish
        """
        await super().publish(event)
        self._published.append(event)

    def has_published(self, pattern: str) -> bool:
        """Check if event was published.

        This method checks if an event matching pattern was published.

        Args:
            pattern: Event pattern to match

        Returns:
            bool: True if matching event was published

        Examples:
            ```python
            assert bus.has_published("user.created")
            assert bus.has_published("user.*")
            ```
        """
        return any(match_pattern(pattern, event.name) for event in self._published)

    def published_count(self, pattern: str) -> int:
        """Count published events.

        This method counts events matching pattern.

        Args:
            pattern: Event pattern to match

        Returns:
            int: Number of matching events

        Examples:
            ```python
            assert bus.published_count("user.created") == 1
            assert bus.published_count("user.*") == 2
            ```
        """
        return sum(1 for event in self._published if match_pattern(pattern, event.name))

    def clear_published(self) -> None:
        """Clear published events.

        This method clears the list of published events.

        Examples:
            ```python
            bus.clear_published()
            assert bus.published_count("*") == 0
            ```
        """
        self._published.clear()


class EventRecorder(EventHandler):
    """Event recorder.

    This class records events for testing.
    It provides methods for event assertions and inspection.

    Features:
    - Event recording
    - Event assertions
    - Event inspection
    - Pattern matching

    Examples:
        ```python
        # Create recorder
        recorder = EventRecorder()
        await bus.subscribe("user.*", recorder)

        # Publish events
        event = Event(name="user.created", data={"id": "123"})
        await bus.publish(event)

        # Assert events
        assert recorder.has_event("user.created")
        assert recorder.count("user.*") == 1
        assert recorder.last_event.name == "user.created"
        ```
    """

    def __init__(self) -> None:
        """Initialize event recorder."""
        self._events: List[Event] = []

    @property
    def id(self) -> str:
        """Get recorder ID.

        Returns:
            str: Always returns "event_recorder"
        """
        return "event_recorder"

    @property
    def data(self) -> Dict[str, int]:
        """Get recorder data.

        Returns:
            Dict containing recorder state:
            - events: Number of recorded events
        """
        return {"events": len(self._events)}

    @property
    def events(self) -> List[Event]:
        """Get recorded events.

        Returns:
            List[Event]: List of recorded events
        """
        return self._events

    @property
    def last_event(self) -> Optional[Event]:
        """Get last recorded event.

        Returns:
            Optional[Event]: Last event if available
        """
        return self._events[-1] if self._events else None

    async def handle(self, event: Event) -> None:
        """Handle event.

        This method records the event.

        Args:
            event: Event to record
        """
        self._events.append(event)
        logger.debug(f"Recorded event {event.name}")

    def has_event(self, pattern: str) -> bool:
        """Check if event was recorded.

        This method checks if an event matching pattern was recorded.

        Args:
            pattern: Event pattern to match

        Returns:
            bool: True if matching event was recorded

        Examples:
            ```python
            assert recorder.has_event("user.created")
            assert recorder.has_event("user.*")
            ```
        """
        return any(match_pattern(pattern, event.name) for event in self._events)

    def count(self, pattern: str) -> int:
        """Count recorded events.

        This method counts events matching pattern.

        Args:
            pattern: Event pattern to match

        Returns:
            int: Number of matching events

        Examples:
            ```python
            assert recorder.count("user.created") == 1
            assert recorder.count("user.*") == 2
            ```
        """
        return sum(1 for event in self._events if match_pattern(pattern, event.name))

    def clear(self) -> None:
        """Clear recorded events.

        This method clears the list of recorded events.

        Examples:
            ```python
            recorder.clear()
            assert recorder.count("*") == 0
            ```
        """
        self._events.clear()


class MockEventHandler(LifecycleAware):
    """Mock event handler for testing."""

    def __init__(self, pattern: str) -> None:
        """Initialize handler."""
        self._pattern = pattern
        self._events: list[Any] = []

    @property
    def id(self) -> str:
        """Get handler ID."""
        return f"mock_handler_{self._pattern}"

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        return {"pattern": self._pattern, "events": len(self._events)}

    async def handle(self, event: Any) -> None:
        """Handle event."""
        self._events.append(event)


class MockEventBus(LifecycleAware):
    """Mock event bus for testing."""

    def __init__(self) -> None:
        """Initialize bus."""
        self._handlers: Dict[str, list[Any]] = {}
        self._events: list[Any] = []

    @property
    def id(self) -> str:
        """Get bus ID."""
        return "mock_event_bus"

    @property
    def data(self) -> Dict[str, Any]:
        """Get bus data."""
        return {"handlers": len(self._handlers), "events": len(self._events)}
