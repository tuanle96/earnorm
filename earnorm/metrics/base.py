"""Base interfaces for metrics collection."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class MetricsManager(ABC):
    """Base metrics manager interface."""

    @abstractmethod
    async def track_validation(
        self,
        model: str,
        field: str,
        validator: str,
        value: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track validation result.

        Args:
            model: Model name
            field: Field name
            validator: Validator name
            value: Validated value
            success: Whether validation succeeded
            error: Optional error message
        """
        pass

    @abstractmethod
    async def track_event(
        self,
        event: str,
        model: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track event.

        Args:
            event: Event name
            model: Model name
            success: Whether event succeeded
            error: Optional error message
        """
        pass

    @abstractmethod
    async def track_access_granted(
        self,
        user_id: str,
        model: str,
        operation: str,
    ) -> None:
        """Track access granted.

        Args:
            user_id: User ID
            model: Model name
            operation: Operation name
        """
        pass

    @abstractmethod
    async def track_access_denied(
        self,
        user_id: str,
        model: str,
        operation: str,
        reason: str,
    ) -> None:
        """Track access denied.

        Args:
            user_id: User ID
            model: Model name
            operation: Operation name
            reason: Denial reason
        """
        pass

    @abstractmethod
    async def track_db_operation(
        self,
        operation: str,
        collection: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track database operation.

        Args:
            operation: Operation name
            collection: Collection name
            duration: Operation duration in seconds
            success: Whether operation succeeded
            error: Optional error message
        """
        pass

    @abstractmethod
    async def track_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool = False,
    ) -> None:
        """Track cache operation.

        Args:
            operation: Operation name (get/set/delete)
            key: Cache key
            hit: Whether operation was a cache hit
        """
        pass

    @abstractmethod
    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get metrics.

        Args:
            metric_type: Optional metric type filter
            start_time: Optional start time filter (timestamp)
            end_time: Optional end time filter (timestamp)

        Returns:
            Dictionary of metrics
        """
        pass
