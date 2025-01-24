"""Connection pools for monitoring module."""

import logging
from typing import Any, Dict, Optional

from earnorm.pool.config import PoolConfig
from earnorm.pool.context import ConnectionContext
from earnorm.pool.core.pool import BasePool
from earnorm.pool.protocols import ConnectionProtocol

logger = logging.getLogger(__name__)


class MetricsConnection(ConnectionProtocol):
    """Connection for metrics storage."""

    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute metrics operation.

        Args:
            operation: Operation name
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            NotImplementedError: If operation is not supported
        """
        if operation == "store":
            return await self.store(args[0])
        raise NotImplementedError(f"Unknown operation: {operation}")

    async def store(self, metrics: Dict[str, Any]) -> None:
        """Store metrics.

        Args:
            metrics: Metrics data to store

        Raises:
            NotImplementedError: This is a base class method
        """
        raise NotImplementedError


class NotificationConnection(ConnectionProtocol):
    """Connection for notification service."""

    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute notification operation.

        Args:
            operation: Operation name
            *args: Operation arguments
            **kwargs: Operation keyword arguments

        Returns:
            Operation result

        Raises:
            NotImplementedError: If operation is not supported
        """
        if operation == "send":
            return await self.send(args[0])
        raise NotImplementedError(f"Unknown operation: {operation}")

    async def send(self, notification: Dict[str, Any]) -> None:
        """Send notification.

        Args:
            notification: Notification data to send

        Raises:
            NotImplementedError: This is a base class method
        """
        raise NotImplementedError


class MetricsPool(BasePool[MetricsConnection]):
    """Pool for metrics storage connections.

    Examples:
        >>> config = PoolConfig(
        ...     min_size=5,
        ...     max_size=20,
        ...     max_idle_time=60,
        ...     connection_timeout=5
        ... )
        >>> pool = MetricsPool(config)
        >>> async with ConnectionContext[MetricsConnection](pool) as conn:
        ...     await conn.store_metrics(metrics)
    """

    def __init__(self, config: PoolConfig) -> None:
        """Initialize metrics pool.

        Args:
            config: Pool configuration
        """
        super().__init__(
            backend_type="metrics",  # type: ignore
            min_size=config.min_size,
            max_size=config.max_size,
            timeout=config.connection_timeout,
            max_lifetime=config.max_lifetime,
            idle_timeout=config.max_idle_time,
            validate_on_borrow=config.validate_on_borrow,
            test_on_return=config.test_on_return,
            **(config.extra_config or {}),
        )
        self._storage_type: Optional[str] = None

    async def store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store metrics using pooled connection.

        Args:
            metrics: Metrics data to store

        Raises:
            Exception: If storing metrics fails
        """
        async with ConnectionContext[MetricsConnection](self) as conn:
            try:
                await conn.execute("store", metrics)
            except Exception as e:
                logger.error(f"Failed to store metrics: {e}")
                raise


class NotificationPool(BasePool[NotificationConnection]):
    """Pool for notification service connections.

    Examples:
        >>> config = PoolConfig(
        ...     min_size=2,
        ...     max_size=10,
        ...     max_idle_time=30,
        ...     connection_timeout=3
        ... )
        >>> pool = NotificationPool(config)
        >>> async with ConnectionContext[NotificationConnection](pool) as conn:
        ...     await conn.send_notification(alert)
    """

    def __init__(self, config: PoolConfig) -> None:
        """Initialize notification pool.

        Args:
            config: Pool configuration
        """
        super().__init__(
            backend_type="notifications",  # type: ignore
            min_size=config.min_size,
            max_size=config.max_size,
            timeout=config.connection_timeout,
            max_lifetime=config.max_lifetime,
            idle_timeout=config.max_idle_time,
            validate_on_borrow=config.validate_on_borrow,
            test_on_return=config.test_on_return,
            **(config.extra_config or {}),
        )
        self._notification_type: Optional[str] = None

    async def send_notification(self, notification: Dict[str, Any]) -> None:
        """Send notification using pooled connection.

        Args:
            notification: Notification data to send

        Raises:
            Exception: If sending notification fails
        """
        async with ConnectionContext[NotificationConnection](self) as conn:
            try:
                await conn.execute("send", notification)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                raise
