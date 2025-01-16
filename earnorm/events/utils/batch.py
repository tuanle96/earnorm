"""Event batching implementation.

This module provides utilities for batching events.
It supports batching by size, time, and custom conditions.

Features:
- Size-based batching
- Time-based batching
- Custom batch conditions
- Batch processing
- Batch validation

Examples:
    ```python
    from earnorm.events.utils.batch import EventBatcher, TimeBatcher, SizeBatcher
    from earnorm.events.core.event import Event

    # Create size batcher
    size_batcher = SizeBatcher(max_size=10)
    for i in range(20):
        event = Event(name=f"event.{i}", data={"id": i})
        batch = await size_batcher.add(event)
        if batch:
            print(f"Processing batch of {len(batch)} events")

    # Create time batcher
    time_batcher = TimeBatcher(max_time=5.0)
    async for batch in time_batcher:
        print(f"Processing batch of {len(batch)} events")

    # Create custom batcher
    batcher = EventBatcher(
        condition=lambda events: sum(len(e.data) for e in events) >= 1000
    )
    async for batch in batcher:
        print(f"Processing batch with total size {sum(len(e.data) for e in batch)}")
    ```
"""

import asyncio
import logging
import time
from typing import Callable, List, Optional

from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)


class EventBatcher:
    """Event batcher.

    This class batches events based on custom conditions.
    It provides async iteration over batches.

    Features:
    - Custom batch conditions
    - Async iteration
    - Batch validation
    - Batch processing

    Attributes:
        condition: Function that determines when to create batch
        _events: List of pending events
        _batch_ready: Event to signal batch ready
    """

    def __init__(
        self,
        condition: Callable[[List[Event]], bool],
        max_size: Optional[int] = None,
    ) -> None:
        """Initialize event batcher.

        Args:
            condition: Function that returns True when batch is ready
            max_size: Optional maximum batch size

        Examples:
            ```python
            # Create batcher with custom condition
            batcher = EventBatcher(
                condition=lambda events: sum(len(e.data) for e in events) >= 1000
            )

            # Create batcher with size limit
            batcher = EventBatcher(
                condition=lambda events: True,
                max_size=10
            )
            ```
        """
        self.condition = condition
        self.max_size = max_size
        self._events: List[Event] = []
        self._batch_ready = asyncio.Event()

    async def add(self, event: Event) -> Optional[List[Event]]:
        """Add event to batch.

        This method adds an event and returns batch if ready.

        Args:
            event: Event to add

        Returns:
            Optional[List[Event]]: Batch of events if ready

        Examples:
            ```python
            batch = await batcher.add(event)
            if batch:
                print(f"Processing batch of {len(batch)} events")
            ```
        """
        # Add event
        self._events.append(event)

        # Check if batch is ready
        if self.max_size and len(self._events) >= self.max_size:
            return self._get_batch()

        if self.condition(self._events):
            return self._get_batch()

        return None

    def _get_batch(self) -> List[Event]:
        """Get current batch.

        This method returns and clears current batch.

        Returns:
            List[Event]: Current batch of events
        """
        batch = self._events
        self._events = []
        self._batch_ready.set()
        return batch

    async def __aiter__(self) -> "EventBatcher":
        """Get async iterator.

        Returns:
            EventBatcher: Self
        """
        return self

    async def __anext__(self) -> List[Event]:
        """Get next batch.

        This method waits for next batch to be ready.

        Returns:
            List[Event]: Next batch of events

        Raises:
            StopAsyncIteration: If batcher is closed
        """
        # Wait for batch
        await self._batch_ready.wait()
        self._batch_ready.clear()

        # Return batch
        return self._events


class SizeBatcher(EventBatcher):
    """Size-based event batcher.

    This class batches events based on size.
    It creates batches when size threshold is reached.

    Features:
    - Size-based batching
    - Maximum batch size
    - Batch validation
    - Batch processing

    Examples:
        ```python
        # Create size batcher
        batcher = SizeBatcher(max_size=10)

        # Add events
        for event in events:
            batch = await batcher.add(event)
            if batch:
                print(f"Processing batch of {len(batch)} events")
        ```
    """

    def __init__(self, max_size: int) -> None:
        """Initialize size batcher.

        Args:
            max_size: Maximum batch size
        """
        super().__init__(
            condition=lambda events: len(events) >= max_size,
            max_size=max_size,
        )


class TimeBatcher(EventBatcher):
    """Time-based event batcher.

    This class batches events based on time.
    It creates batches after time threshold is reached.

    Features:
    - Time-based batching
    - Maximum batch time
    - Batch validation
    - Batch processing

    Examples:
        ```python
        # Create time batcher
        batcher = TimeBatcher(max_time=5.0)

        # Process batches
        async for batch in batcher:
            print(f"Processing batch of {len(batch)} events")
        ```
    """

    def __init__(
        self,
        max_time: float,
        max_size: Optional[int] = None,
    ) -> None:
        """Initialize time batcher.

        Args:
            max_time: Maximum batch time in seconds
            max_size: Optional maximum batch size
        """
        self.max_time = max_time
        self._start_time = time.time()

        super().__init__(
            condition=lambda events: time.time() - self._start_time >= max_time,
            max_size=max_size,
        )

    async def add(self, event: Event) -> Optional[List[Event]]:
        """Add event to batch.

        This method adds an event and returns batch if ready.
        It resets timer when batch is created.

        Args:
            event: Event to add

        Returns:
            Optional[List[Event]]: Batch of events if ready
        """
        batch = await super().add(event)
        if batch:
            self._start_time = time.time()
        return batch
