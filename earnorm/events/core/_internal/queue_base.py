"""Base class for queue implementations."""

import abc
from typing import Any, Dict, List, Optional, Protocol

from earnorm.events.core.event import Event


class QueueProtocol(Protocol):
    """Protocol for queue implementations."""

    @property
    def connected(self) -> bool:
        """Whether connected to message broker."""
        ...

    async def connect(self, broker_uri: str) -> bool:
        """Connect to message broker.

        Args:
            broker_uri: Message broker connection URI

        Returns:
            bool: True if connected successfully
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from message broker."""
        ...

    async def push(self, event: Event, delay: Optional[float] = None) -> None:
        """Push event to queue.

        Args:
            event: Event to push
            delay: Optional delay in seconds

        Raises:
            RuntimeError: If not connected to message broker
        """
        ...

    async def get_failed_jobs(self) -> List[Any]:
        """Get list of failed jobs.

        Returns:
            List of failed jobs

        Raises:
            RuntimeError: If not connected to message broker
        """
        ...

    async def retry_job(self, job_id: str) -> None:
        """Retry failed job.

        Args:
            job_id: Job ID to retry

        Raises:
            RuntimeError: If not connected to message broker
        """
        ...

    async def remove_job(self, job_id: str) -> None:
        """Remove job from queue.

        Args:
            job_id: Job ID to remove

        Raises:
            RuntimeError: If not connected to message broker
        """
        ...


class QueueBase(abc.ABC):
    """Base class for queue implementations."""

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
        self.queue_name = queue_name
        self.retry_policy = retry_policy or {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        }

    @property
    @abc.abstractmethod
    def connected(self) -> bool:
        """Whether connected to message broker."""
        pass

    @abc.abstractmethod
    async def connect(self, broker_uri: str) -> bool:
        """Connect to message broker.

        Args:
            broker_uri: Message broker connection URI

        Returns:
            bool: True if connected successfully
        """
        pass

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker."""
        pass

    @abc.abstractmethod
    async def push(self, event: Event, delay: Optional[float] = None) -> None:
        """Push event to queue.

        Args:
            event: Event to push
            delay: Optional delay in seconds

        Raises:
            RuntimeError: If not connected to message broker
        """
        pass

    @abc.abstractmethod
    async def get_failed_jobs(self) -> List[Any]:
        """Get list of failed jobs.

        Returns:
            List of failed jobs

        Raises:
            RuntimeError: If not connected to message broker
        """
        pass

    @abc.abstractmethod
    async def retry_job(self, job_id: str) -> None:
        """Retry failed job.

        Args:
            job_id: Job ID to retry

        Raises:
            RuntimeError: If not connected to message broker
        """
        pass

    @abc.abstractmethod
    async def remove_job(self, job_id: str) -> None:
        """Remove job from queue.

        Args:
            job_id: Job ID to remove

        Raises:
            RuntimeError: If not connected to message broker
        """
        pass
