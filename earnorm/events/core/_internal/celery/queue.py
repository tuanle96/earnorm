"""Celery queue implementation."""

import logging
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult  # type: ignore

from earnorm.events.core._internal.connection import ConnectionManager
from earnorm.events.core._internal.queue_base import QueueBase
from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)


class CeleryQueue(QueueBase):
    """Celery queue implementation."""

    def __init__(
        self,
        queue_name: str = "earnorm:events",
        retry_policy: Optional[Dict[str, Any]] = None,
    ):
        """Initialize queue.

        Args:
            queue_name: Queue name
            retry_policy: Retry policy configuration
        """
        super().__init__(queue_name=queue_name, retry_policy=retry_policy)
        self._connection: Optional[ConnectionManager] = None

    @property
    def connected(self) -> bool:
        """Whether connected to Redis."""
        return bool(self._connection and self._connection.connected)

    async def connect(self, broker_uri: str) -> bool:
        """Connect to Redis and initialize Celery.

        Args:
            broker_uri: Redis connection URI

        Returns:
            bool: True if connected successfully
        """
        if self.connected:
            return True

        self._connection = ConnectionManager(
            redis_uri=broker_uri,
            queue_name=self.queue_name,
        )
        return await self._connection.connect()

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._connection:
            await self._connection.disconnect()
            self._connection = None

    async def push(self, event: Event, delay: Optional[float] = None) -> None:
        """Push event to queue.

        Args:
            event: Event to push
            delay: Optional delay in seconds

        Raises:
            RuntimeError: If not connected to Redis
        """
        if (
            not self.connected
            or not self._connection
            or not self._connection.celery_app
        ):
            raise RuntimeError("Not connected to Redis")

        try:
            # Convert event to dict
            event_data = event.to_dict()

            # Get task
            task = self._connection.celery_app.task(  # type: ignore
                name="process_event",
                bind=True,
                base=self._connection.celery_app.Task,  # type: ignore
            )

            # Schedule task
            result = task.apply_async(  # type: ignore
                args=[event_data],
                countdown=int(delay) if delay else None,
                queue=self.queue_name,
                retry=True,
                retry_policy=self.retry_policy,
            )

            # Store task ID in event
            event.job_id = result.id  # type: ignore
            logger.debug(f"Pushed event {event.name} to queue with task ID {result.id}")  # type: ignore

        except Exception as e:
            logger.error(f"Failed to push event {event.name} to queue: {str(e)}")
            raise

    async def get_failed_jobs(self) -> List[AsyncResult]:
        """Get list of failed jobs.

        Returns:
            List of failed jobs

        Raises:
            RuntimeError: If not connected to Redis
        """
        if (
            not self.connected
            or not self._connection
            or not self._connection.celery_app
        ):
            raise RuntimeError("Not connected to Redis")

        try:
            # Get all tasks from queue
            i = self._connection.celery_app.control.inspect()  # type: ignore
            failed = i.failed() or {}  # type: ignore

            # Convert to AsyncResult objects
            return [
                AsyncResult(task["id"]) for tasks in failed.values() for task in tasks  # type: ignore
            ]

        except Exception as e:
            logger.error(f"Error getting failed jobs: {str(e)}")
            raise

    async def retry_job(self, job_id: str) -> None:
        """Retry failed job.

        Args:
            job_id: Job ID to retry

        Raises:
            RuntimeError: If not connected to Redis
        """
        if (
            not self.connected
            or not self._connection
            or not self._connection.celery_app
        ):
            raise RuntimeError("Not connected to Redis")

        try:
            result = AsyncResult(job_id, app=self._connection.celery_app)  # type: ignore
            if result.failed():
                result.retry()  # type: ignore
                logger.info(f"Retrying job {job_id}")
            else:
                logger.warning(f"Job {job_id} is not failed")

        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {str(e)}")
            raise

    async def remove_job(self, job_id: str) -> None:
        """Remove job from queue.

        Args:
            job_id: Job ID to remove

        Raises:
            RuntimeError: If not connected to Redis
        """
        if (
            not self.connected
            or not self._connection
            or not self._connection.celery_app
        ):
            raise RuntimeError("Not connected to Redis")

        try:
            result = AsyncResult(job_id, app=self._connection.celery_app)  # type: ignore
            result.revoke(terminate=True)  # type: ignore
            logger.info(f"Removed job {job_id}")

        except Exception as e:
            logger.error(f"Error removing job {job_id}: {str(e)}")
            raise
