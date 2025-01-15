"""Event bus implementation."""

import logging
from typing import Any, Callable, Dict, List, Optional

from earnorm.events.core._internal.celery.queue import CeleryQueue
from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Any]


class EventBus:
    """Event bus for publishing and subscribing to events."""

    def __init__(
        self,
        redis_uri: str,
        queue_name: str = "earnorm:events",
        retry_policy: Optional[Dict[str, Any]] = None,
    ):
        """Initialize event bus.

        Args:
            redis_uri: Redis connection URI
            queue_name: Queue name
            retry_policy: Retry policy configuration
        """
        self.redis_uri = redis_uri
        self.queue_name = queue_name
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._queue = CeleryQueue(queue_name=queue_name, retry_policy=retry_policy)

    async def connect(self) -> None:
        """Connect to event bus."""
        if not await self._queue.connect(self.redis_uri):
            raise RuntimeError("Failed to connect to Redis")
        logger.info("Event bus connected")

    async def disconnect(self) -> None:
        """Disconnect from event bus."""
        await self._queue.disconnect()
        logger.info("Event bus disconnected")

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Subscribe to event.

        Args:
            event_name: Event name to subscribe to
            handler: Event handler function
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
        logger.debug(f"Subscribed handler to event {event_name}")

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Unsubscribe from event.

        Args:
            event_name: Event name to unsubscribe from
            handler: Event handler function
        """
        if event_name in self._handlers:
            self._handlers[event_name].remove(handler)
            if not self._handlers[event_name]:
                del self._handlers[event_name]
            logger.debug(f"Unsubscribed handler from event {event_name}")

    async def publish(self, event: Event, delay: Optional[float] = None) -> None:
        """Publish event.

        Args:
            event: Event to publish
            delay: Optional delay in seconds
        """
        await self._queue.push(event, delay=delay)
        logger.debug(f"Published event {event.name}")

    async def get_failed_jobs(self) -> List[Any]:
        """Get list of failed jobs.

        Returns:
            List of failed jobs
        """
        return await self._queue.get_failed_jobs()

    async def retry_job(self, job_id: str) -> None:
        """Retry failed job.

        Args:
            job_id: Job ID to retry
        """
        await self._queue.retry_job(job_id)

    async def remove_job(self, job_id: str) -> None:
        """Remove job.

        Args:
            job_id: Job ID to remove
        """
        await self._queue.remove_job(job_id)
