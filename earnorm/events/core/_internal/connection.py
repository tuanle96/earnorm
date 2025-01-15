"""Connection manager for Redis and Celery."""

import asyncio
import logging
from typing import Optional

import redis.asyncio as redis
from celery import Celery  # type: ignore
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages Redis and Celery connections with automatic reconnection and health checking."""

    def __init__(
        self,
        redis_uri: str,
        queue_name: str = "earnorm:events",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        health_check_interval: float = 30.0,
    ):
        """Initialize connection manager.

        Args:
            redis_uri: Redis connection URI
            queue_name: Queue name for Celery
            max_retries: Maximum number of reconnection attempts
            retry_delay: Initial delay between retries in seconds (uses exponential backoff)
            health_check_interval: Interval between health checks in seconds
        """
        self.redis_uri = redis_uri
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval

        self._redis_client: Redis | None = None
        self._celery_app: Optional[Celery] = None
        self._connected = False
        self._health_check_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> bool:
        """Connect to Redis server with retry.

        Returns:
            bool: True if connected successfully
        """
        if self._connected and self._redis_client:
            return True

        retries = 0
        current_delay = self.retry_delay

        while retries < self.max_retries:
            try:
                # Create Redis client
                self._redis_client = redis.Redis.from_url(  # type: ignore[misc]
                    self.redis_uri, decode_responses=True, encoding="utf-8"
                )

                # Test connection
                await self._redis_client.ping()  # type: ignore[no-any-return]
                self._connected = True

                # Initialize Celery app
                self._celery_app = Celery(
                    "earnorm",
                    broker=self.redis_uri,
                    backend=self.redis_uri,
                )
                self._celery_app.conf.update(  # type: ignore
                    task_serializer="json",
                    accept_content=["json"],
                    result_serializer="json",
                    timezone="UTC",
                    enable_utc=True,
                    task_default_queue=self.queue_name,
                    task_default_exchange=self.queue_name,
                    task_default_routing_key=self.queue_name,
                    task_track_started=True,
                    task_publish_retry=True,
                    task_publish_retry_policy={
                        "max_retries": 3,
                        "interval_start": 0,
                        "interval_step": 0.2,
                        "interval_max": 0.5,
                    },
                )

                # Start health check
                if not self._health_check_task:
                    self._health_check_task = asyncio.create_task(self._health_check())

                logger.info("Successfully connected to Redis and initialized Celery")
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
        """Disconnect from Redis server."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

        self._connected = False
        logger.info("Disconnected from Redis")

    async def _health_check(self) -> None:
        """Periodically checks Redis connection health and attempts reconnection if needed."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                if self._redis_client is None:
                    raise RedisError("No Redis client")

                await self._redis_client.ping()  # type: ignore[no-any-return]

            except RedisError as e:
                logger.warning(f"Redis health check failed: {str(e)}")
                self._connected = False
                await self.connect()

            except asyncio.CancelledError:
                break

    @property
    def connected(self) -> bool:
        """Whether connected to Redis."""
        return self._connected

    @property
    def redis_client(self) -> Optional[Redis]:
        """Get Redis client."""
        return self._redis_client

    @property
    def celery_app(self) -> Optional[Celery]:
        """Get Celery app."""
        return self._celery_app
