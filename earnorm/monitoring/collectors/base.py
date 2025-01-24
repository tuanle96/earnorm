"""Base collector for monitoring."""

from datetime import datetime, timezone
from typing import Sequence

from earnorm.monitoring.interfaces import CollectorInterface
from earnorm.monitoring.metrics import Metric


class BaseCollector(CollectorInterface):
    """Base collector for monitoring.

    Examples:
        >>> class SystemCollector(BaseCollector):
        ...     def __init__(self) -> None:
        ...         super().__init__("system", 60)  # Collect every 60 seconds
        ...
        ...     async def collect(self) -> Sequence[Metric]:
        ...         # Collect system metrics
        ...         return [
        ...             Metric("cpu_usage", 0.5),
        ...             Metric("memory_usage", 1024 * 1024),
        ...         ]
    """

    def __init__(self, name: str, interval: int) -> None:
        """Initialize collector.

        Args:
            name: Collector name.
            interval: Collection interval in seconds.
        """
        self._name: str = name
        self._interval: int = interval
        self._last_collection: datetime = datetime.min.replace(tzinfo=timezone.utc)

    @property
    def name(self) -> str:
        """Get collector name.

        Returns:
            str: Collector name.
        """
        return self._name

    @property
    def interval(self) -> int:
        """Get collection interval in seconds.

        Returns:
            int: Collection interval in seconds.
        """
        return self._interval

    def should_collect(self) -> bool:
        """Check if collector should collect metrics.

        Returns:
            bool: True if collector should collect metrics, False otherwise.
        """
        now: datetime = datetime.now(timezone.utc)
        if (now - self._last_collection).total_seconds() >= self._interval:
            self._last_collection = now
            return True
        return False

    async def collect(self) -> Sequence[Metric]:
        """Collect metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Collector must implement collect method")
