"""Application metrics collector."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.collectors import BaseCollector
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class ApplicationCollector(BaseCollector):
    """Application collector for monitoring.

    Examples:
        >>> collector = ApplicationCollector()
        >>> # Track HTTP request
        >>> await collector.track_request("/api/users", "GET", 0.1, 200)
        >>> # Track cache operation
        >>> await collector.track_cache_operation("get", True)
        >>> # Track database query
        >>> await collector.track_database_query("users.find", 0.05)
        >>> # Collect metrics
        >>> metrics = await collector.collect()
        >>> for metric in metrics:
        ...     print(f"{metric.name}: {metric.value}")
        http_requests_total: 1
        http_request_duration_seconds: 0.1
        http_request_errors_total: 0
        cache_hits_total: 1
        cache_misses_total: 0
        database_queries_total: 1
        database_query_duration_seconds: 0.05
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        interval: int = 30,
    ) -> None:
        """Initialize application collector.

        Args:
            event_bus: Event bus for emitting metrics
            interval: Collection interval in seconds
        """
        super().__init__("application", interval)
        self._event_bus = event_bus

        # HTTP metrics
        self._http_requests = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            {"type": "total"},
        )
        self._http_errors = Counter(
            "http_request_errors_total",
            "Total number of HTTP errors",
            {"type": "error"},
        )
        self._http_latency = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
        )
        self._http_status = Counter(
            "http_response_status_total",
            "Total number of HTTP responses by status code",
        )
        self._http_size = Histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
        )

        # Cache metrics
        self._cache_hits = Counter(
            "cache_hits_total",
            "Total number of cache hits",
            {"type": "hit"},
        )
        self._cache_misses = Counter(
            "cache_misses_total",
            "Total number of cache misses",
            {"type": "miss"},
        )
        self._cache_latency = Histogram(
            "cache_operation_duration_seconds",
            "Cache operation duration in seconds",
        )

        # Database metrics
        self._db_queries = Counter(
            "database_queries_total",
            "Total number of database queries",
            {"type": "total"},
        )
        self._db_errors = Counter(
            "database_query_errors_total",
            "Total number of database query errors",
            {"type": "error"},
        )
        self._db_latency = Histogram(
            "database_query_duration_seconds",
            "Database query duration in seconds",
        )

        # Register all metrics
        self._metrics: Dict[str, Counter | Gauge | Histogram] = {
            "http_requests": self._http_requests,
            "http_errors": self._http_errors,
            "http_latency": self._http_latency,
            "http_status": self._http_status,
            "http_size": self._http_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_latency": self._cache_latency,
            "db_queries": self._db_queries,
            "db_errors": self._db_errors,
            "db_latency": self._db_latency,
        }

    async def track_request(
        self,
        path: str,
        method: str,
        duration: float,
        status: int,
        size: Optional[int] = None,
    ) -> None:
        """Track HTTP request.

        Args:
            path: Request path
            method: HTTP method
            duration: Request duration in seconds
            status: HTTP status code
            size: Response size in bytes

        Raises:
            Exception: If unable to track HTTP request
        """
        try:
            # Update request metrics
            self._http_requests.inc()
            self._http_latency.observe(duration)

            # Update status with labels
            labels = {"status": str(status), "method": method, "path": path}
            self._http_status.update_labels(labels)
            self._http_status.inc()

            # Track errors (status >= 400)
            if status >= 400:
                self._http_errors.update_labels(labels)
                self._http_errors.inc()

            # Track response size if provided
            if size is not None:
                self._http_size.observe(float(size))

            # Emit event if event bus is available
            if self._event_bus:
                event_data: Dict[str, Any] = {
                    "collector": self.name,
                    "type": "http",
                    "path": path,
                    "method": method,
                    "duration": duration,
                    "status": status,
                    "size": size,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                event = Event(name="metrics.collected", data=event_data)
                await self._event_bus.publish(event)
        except Exception as e:
            logger.exception("Error tracking HTTP request: %s", e)
            raise

    async def track_cache_operation(
        self,
        operation: str,
        hit: bool,
        duration: Optional[float] = None,
    ) -> None:
        """Track cache operation.

        Args:
            operation: Cache operation (get, set, delete, etc.)
            hit: Whether the operation was a cache hit
            duration: Operation duration in seconds

        Raises:
            Exception: If unable to track cache operation
        """
        try:
            # Update cache metrics
            labels = {"operation": operation}
            if hit:
                self._cache_hits.update_labels(labels)
                self._cache_hits.inc()
            else:
                self._cache_misses.update_labels(labels)
                self._cache_misses.inc()

            # Track latency if provided
            if duration is not None:
                self._cache_latency.observe(duration)

            # Emit event if event bus is available
            if self._event_bus:
                event_data: Dict[str, Any] = {
                    "collector": self.name,
                    "type": "cache",
                    "operation": operation,
                    "hit": hit,
                    "duration": duration,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                event = Event(name="metrics.collected", data=event_data)
                await self._event_bus.publish(event)
        except Exception as e:
            logger.exception("Error tracking cache operation: %s", e)
            raise

    async def track_database_query(
        self,
        query: str,
        duration: float,
        error: Optional[str] = None,
    ) -> None:
        """Track database query.

        Args:
            query: Query identifier or type
            duration: Query duration in seconds
            error: Error message if query failed

        Raises:
            Exception: If unable to track database query
        """
        try:
            # Update database metrics
            labels = {"query": query}
            self._db_queries.update_labels(labels)
            self._db_queries.inc()
            self._db_latency.observe(duration)

            # Track errors if any
            if error:
                labels["error"] = error
                self._db_errors.update_labels(labels)
                self._db_errors.inc()

            # Emit event if event bus is available
            if self._event_bus:
                event_data: Dict[str, Any] = {
                    "collector": self.name,
                    "type": "database",
                    "query": query,
                    "duration": duration,
                    "error": error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                event = Event(name="metrics.collected", data=event_data)
                await self._event_bus.publish(event)
        except Exception as e:
            logger.exception("Error tracking database query: %s", e)
            raise

    async def collect(self) -> Sequence[Metric]:
        """Collect application metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            Exception: If unable to collect metrics.
        """
        try:
            # Convert metrics to Metric objects
            metrics = [
                Metric(
                    name=metric.name,
                    value=metric.value,
                    description=metric.description,
                    tags=metric.labels,
                    timestamp=datetime.now(timezone.utc),
                )
                for metric in self._metrics.values()
            ]
            return metrics
        except Exception:
            logger.error("Error collecting application metrics", exc_info=True)
            raise
