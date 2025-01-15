"""Redis queue implementation."""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional, cast

from redis.asyncio import Redis

from .event import Event

logger = logging.getLogger(__name__)


class RedisEventQueue:
    """Redis-based event queue implementation."""

    def __init__(
        self,
        redis: Redis,
        queue_name: str = "earnorm:events",
        processing_queue: str = "earnorm:events:processing",
        failed_queue: str = "earnorm:events:failed",
        scheduled_queue: str = "earnorm:events:scheduled",
    ):
        """Initialize Redis queue.

        Args:
            redis: Redis client instance
            queue_name: Main queue name
            processing_queue: Processing queue name
            failed_queue: Failed queue name
            scheduled_queue: Scheduled queue name
        """
        self.redis = redis
        self.queue_name = queue_name
        self.processing_queue = processing_queue
        self.failed_queue = failed_queue
        self.scheduled_queue = scheduled_queue

    async def push(self, event: Event, delay: Optional[float] = None) -> None:
        """Push event to queue.

        Args:
            event: Event to push
            delay: Optional delay in seconds
        """
        event_data = self._serialize_event(event)

        if delay:
            # Add to scheduled queue with score as timestamp
            score = datetime.now().timestamp() + delay
            await self.redis.zadd(self.scheduled_queue, {event_data: score})  # type: ignore[awaitable-type, unused-coroutine, arg-type, return-value]
        else:
            # Add to main queue
            await self.redis.lpush(self.queue_name, event_data)  # type: ignore[awaitable-type, unused-coroutine, arg-type, return-value]

    async def pop_batch(self, batch_size: int = 100, timeout: int = 1) -> List[Event]:
        """Pop batch of events from queue.

        Args:
            batch_size: Maximum number of events to pop
            timeout: Timeout in seconds

        Returns:
            List of events
        """
        # First check scheduled queue
        now = datetime.now().timestamp()
        scheduled: List[Any] = await self.redis.zrangebyscore(
            self.scheduled_queue, min=0, max=now, start=0, num=batch_size
        )

        if scheduled:
            # Move due events to main queue
            pipe = self.redis.pipeline()
            for event_data in scheduled:
                pipe.zrem(self.scheduled_queue, event_data)
                pipe.lpush(self.queue_name, event_data)
            await pipe.execute()

        # Pop from main queue
        events: List[Event] = []
        for _ in range(batch_size):
            # Use BRPOPLPUSH to atomically move to processing queue
            event_data = await self.redis.brpoplpush(
                self.queue_name, self.processing_queue, timeout=timeout
            )

            if not event_data:
                break

            try:
                event = self._deserialize_event(cast(str, event_data))
                events.append(event)
            except Exception as e:
                logger.error(f"Failed to deserialize event: {e}")
                # Move to failed queue
                await self.redis.lrem(self.processing_queue, 1, event_data)
                await self.redis.lpush(self.failed_queue, event_data)

        return events

    async def ack(self, event: Event) -> None:
        """Acknowledge successful processing of event.

        Args:
            event: Processed event
        """
        event_data = self._serialize_event(event)
        await self.redis.lrem(self.processing_queue, 1, event_data)

    async def nack(self, event: Event, error: Exception) -> None:
        """Negative acknowledge failed event processing.

        Args:
            event: Failed event
            error: Processing error
        """
        event_data = self._serialize_event(event)

        # Remove from processing queue
        await self.redis.lrem(self.processing_queue, 1, event_data)

        # Add error info
        event.error = str(error)
        event.failed_at = datetime.now()

        # Move to failed queue
        await self.redis.lpush(self.failed_queue, self._serialize_event(event))

    async def requeue_failed(self) -> int:
        """Requeue failed events to main queue.

        Returns:
            Number of requeued events
        """
        count = 0
        while True:
            event_data = await self.redis.rpoplpush(self.failed_queue, self.queue_name)
            if not event_data:
                break
            count += 1
        return count

    def _serialize_event(self, event: Event) -> str:
        """Serialize event to JSON string.

        Args:
            event: Event to serialize

        Returns:
            JSON string
        """
        return json.dumps(event.to_dict())

    def _deserialize_event(self, event_data: str) -> Event:
        """Deserialize event from JSON string.

        Args:
            event_data: JSON string

        Returns:
            Event instance
        """
        data = json.loads(event_data)
        return Event.from_dict(data)
