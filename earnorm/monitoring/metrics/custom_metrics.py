"""Custom metrics support."""

import functools
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.metrics.base import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
MetricType = Union[Counter, Gauge, Histogram]


class CustomMetric:
    """Decorator for custom metrics.

    Examples:
        >>> @CustomMetric(
        ...     name="request_duration",
        ...     description="Request duration in seconds",
        ...     type="histogram",
        ...     labels={"method": "GET", "endpoint": "/users"},
        ...     buckets=[0.1, 0.5, 1.0],
        ... )
        ... async def handle_request():
        ...     # Function code here
        ...     pass

        >>> @CustomMetric(
        ...     name="active_users",
        ...     description="Number of active users",
        ...     type="gauge",
        ...     labels={"status": "online"},
        ... )
        ... async def get_active_users():
        ...     # Function code here
        ...     pass

        >>> @CustomMetric(
        ...     name="total_requests",
        ...     description="Total number of requests",
        ...     type="counter",
        ...     labels={"method": "POST"},
        ... )
        ... async def process_request():
        ...     # Function code here
        ...     pass
    """

    def __init__(
        self,
        name: str,
        description: str,
        type: str = "counter",
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[list[float]] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        """Initialize custom metric.

        Args:
            name: Metric name
            description: Metric description
            type: Metric type (counter, gauge, or histogram)
            labels: Optional metric labels
            buckets: Optional histogram buckets
            event_bus: Optional event bus for emitting metrics

        Raises:
            ValueError: If metric type is invalid
        """
        self.name = name
        self.description = description
        self.type = type.lower()
        self.labels = labels or {}
        self.buckets = buckets
        self._event_bus = event_bus

        # Create metric based on type
        if self.type == "counter":
            self._metric: MetricType = Counter(name, description, self.labels)
        elif self.type == "gauge":
            self._metric = Gauge(name, description, self.labels)
        elif self.type == "histogram":
            self._metric = Histogram(name, description, self.labels)
        else:
            raise ValueError(f"Invalid metric type: {type}")

    def __call__(self, func: F) -> F:
        """Wrap function to collect metrics.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function

        Raises:
            Exception: If unable to collect metrics
        """

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                if self.type == "counter":
                    counter = cast(Counter, self._metric)
                    counter.inc()
                elif self.type == "gauge":
                    gauge = cast(Gauge, self._metric)
                    gauge.set(1)
                elif self.type == "histogram":
                    histogram = cast(Histogram, self._metric)
                    duration = time.monotonic() - start_time
                    histogram.observe(duration)

                # Emit metric collected event
                if self._event_bus:
                    event_data: Dict[str, Any] = {
                        "metric": self.name,
                        "type": self.type,
                        "value": self._metric.value,
                        "labels": self.labels,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    event = Event(name="metrics.collected", data=event_data)
                    await self._event_bus.publish(event)

                return result
            except Exception as e:
                if self.type == "counter":
                    counter = cast(Counter, self._metric)
                    error_labels = self.labels.copy()
                    error_labels["status"] = "error"
                    counter.update_labels(error_labels)
                    counter.inc()
                logger.exception("Error collecting metric %s: %s", self.name, e)
                raise

        return cast(F, wrapper)
