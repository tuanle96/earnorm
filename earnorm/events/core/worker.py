"""Event worker implementation."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List

from .event import Event
from .queue import RedisEventQueue

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Awaitable[None]]


class Worker:
    """Event worker for processing events from queue."""

    def __init__(
        self,
        queue: RedisEventQueue,
        batch_size: int = 100,
        poll_interval: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        num_workers: int = 1,
    ):
        """Initialize worker.

        Args:
            queue: Event queue instance
            batch_size: Number of events to process in batch
            poll_interval: Interval between queue polls in seconds
            max_retries: Maximum number of retries for failed events
            retry_delay: Delay between retries in seconds
            num_workers: Number of worker tasks
        """
        self.queue = queue
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.num_workers = num_workers

        self._handlers: Dict[str, List[EventHandler]] = {}
        self._running = False
        self._tasks: List[asyncio.Task[None]] = []

    def register_handler(self, event_name: str, handler: EventHandler) -> None:
        """Register event handler.

        Args:
            event_name: Event name to handle
            handler: Event handler function
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    async def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return

        self._running = True
        for _ in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop())
            self._tasks.append(task)

    async def stop(self) -> None:
        """Stop worker tasks."""
        if not self._running:
            return

        self._running = False
        if self._tasks:
            await asyncio.gather(*self._tasks)
            self._tasks.clear()

    async def _worker_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                events = await self.queue.pop_batch(
                    batch_size=self.batch_size, timeout=int(self.poll_interval)
                )

                if not events:
                    await asyncio.sleep(self.poll_interval)
                    continue

                await asyncio.gather(*[self._process_event(event) for event in events])

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_event(self, event: Event) -> None:
        """Process single event.

        Args:
            event: Event to process
        """
        if event.name not in self._handlers:
            logger.warning(f"No handlers for event: {event.name}")
            await self.queue.ack(event)
            return

        retries = event.metadata.get("retries", 0)

        try:
            await asyncio.gather(
                *[handler(event) for handler in self._handlers[event.name]]
            )
            await self.queue.ack(event)

        except Exception as e:
            logger.error(f"Error processing event {event.name}: {e}")

            if retries >= self.max_retries:
                logger.error(f"Max retries reached for event {event.name}")
                await self.queue.nack(event, e)
                return

            # Update retry count and delay
            event.metadata["retries"] = retries + 1
            await self.queue.push(event, delay=self.retry_delay)
            await self.queue.ack(event)  # Remove from processing queue

    async def __aenter__(self) -> "Worker":
        """Start worker on context enter.

        Returns:
            Worker instance
        """
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop worker on context exit.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        await self.stop()
