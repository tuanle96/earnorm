"""Event bus implementation."""

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

from .event import Event
from .queue import RedisEventQueue
from .worker import Worker

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Event bus for publishing and subscribing to events."""

    def __init__(
        self,
        redis_uri: str,
        queue_name: str = "earnorm:events",
        batch_size: int = 100,
        poll_interval: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 5.0,
        num_workers: int = 1,
        health_check_interval: float = 30.0,
    ):
        """Initialize event bus.

        Args:
            redis_uri: Redis connection URI
            queue_name: Event queue name
            batch_size: Number of events to process in batch
            poll_interval: Interval between queue polls in seconds
            max_retries: Maximum number of retries for failed events
            retry_delay: Delay between retries in seconds
            num_workers: Number of worker tasks
            health_check_interval: Interval between health checks in seconds
        """
        self.redis_uri = redis_uri
        self.queue_name = queue_name
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.num_workers = num_workers
        self.health_check_interval = health_check_interval

        self._client: Optional[Redis] = None
        self._queue: Optional[RedisEventQueue] = None
        self._worker: Optional[Worker] = None
        self._connected = False
        self._health_check_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> bool:
        """Connect to Redis server with retry.

        Returns:
            bool: True if connected successfully
        """
        if self._connected and self._client and self._queue and self._worker:
            return True

        retries = 0
        current_delay = self.retry_delay

        while retries < self.max_retries:
            try:
                # Create Redis client
                self._client = Redis.from_url(  # type: ignore[return-value]
                    self.redis_uri, decode_responses=True, encoding="utf-8"
                )

                # Test connection
                await self._client.ping()  # type: ignore[no-any-return]

                # Create queue and worker
                self._queue = RedisEventQueue(
                    redis=self._client, queue_name=self.queue_name
                )

                self._worker = Worker(
                    queue=self._queue,
                    batch_size=self.batch_size,
                    poll_interval=self.poll_interval,
                    max_retries=self.max_retries,
                    retry_delay=self.retry_delay,
                    num_workers=self.num_workers,
                )

                # Start worker
                await self._worker.start()

                # Start health check
                if not self._health_check_task:
                    self._health_check_task = asyncio.create_task(self._health_check())

                self._connected = True
                logger.info("Successfully connected to Redis and started event worker")
                return True

            except RedisError as e:
                retries += 1
                if retries == self.max_retries:
                    logger.error(
                        f"Failed to connect to Redis after {self.max_retries} attempts: {str(e)}"
                    )
                    return False

                logger.warning(
                    f"Failed to connect to Redis (attempt {retries}/{self.max_retries}): {str(e)}"
                )
                await asyncio.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

        return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server and stop worker."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._worker:
            await self._worker.stop()
            self._worker = None

        if self._client:
            await self._client.close()
            self._client = None

        self._queue = None
        self._connected = False
        logger.info("Disconnected from Redis and stopped event worker")

    async def _health_check(self) -> None:
        """Periodically check Redis connection health and attempt reconnection if needed."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                if self._client is None:
                    raise RedisError("No Redis client")

                await self._client.ping()  # type: ignore[no-any-return]

            except RedisError as e:
                logger.warning(f"Redis health check failed: {str(e)}")
                self._connected = False
                await self.connect()

            except asyncio.CancelledError:
                break

    async def publish(self, event: Event, delay: Optional[float] = None) -> None:
        """Publish event to queue.

        Args:
            event: Event to publish
            delay: Optional delay in seconds
        """
        if not self._connected or not self._queue:
            if not await self.connect():
                raise RedisError("Not connected to Redis")

        if self._queue:  # Recheck after connect
            await self._queue.push(event, delay=delay)
        else:
            raise RedisError("Queue not initialized")

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Subscribe handler to event.

        Args:
            event_name: Event name to subscribe to
            handler: Event handler function
        """
        if not self._worker:
            raise RedisError("Event worker not initialized")

        self._worker.register_handler(event_name, handler)

    async def __aenter__(self) -> "EventBus":
        """Start event bus on context enter.

        Returns:
            Event bus instance
        """
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[object],
    ) -> None:
        """Stop event bus on context exit.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        await self.disconnect()
