"""Metrics export for exporting logging metrics."""

import logging
from typing import Any, Dict, Optional, Union

from earnorm.monitoring.metrics.base import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class LogMetrics:
    """Class for exporting logging metrics.

    This class provides functionality to:
    - Track log volume metrics
    - Track error metrics
    - Track latency metrics
    - Track handler metrics
    - Export metrics

    Examples:
        >>> # Track log volume
        >>> metrics = LogMetrics()
        >>> await metrics.record_log({'level': 'info'}, 0.1)
        >>> volume = metrics.get_metric('log_volume_total')
        >>> print(f'Total logs: {volume.value}')

        >>> # Track errors by type
        >>> metrics = LogMetrics()
        >>> await metrics.record_log(
        ...     {'level': 'error', 'error_type': 'ValueError'},
        ...     0.1
        ... )
        >>> errors = metrics.get_metric('error_count_by_type')
        >>> print(f'Errors: {errors.labels}')

        >>> # Track latency percentiles
        >>> metrics = LogMetrics()
        >>> for _ in range(100):
        ...     await metrics.record_log({'level': 'info'}, 0.1)
        >>> latency = metrics.get_metric('log_latency_seconds')
        >>> print(f'P95 latency: {latency.get_percentile(0.95)}')

        >>> # Export all metrics
        >>> metrics = LogMetrics()
        >>> all_metrics = metrics.export()
        >>> for name, metric in all_metrics.items():
        ...     print(f'{name}: {metric.value}')
    """

    def __init__(self):
        """Initialize the log metrics."""
        try:
            # Volume metrics
            self._log_volume: Counter = Counter(
                "log_volume_total", "Total number of log entries"
            )
            self._log_volume_by_level: Counter = Counter(
                "log_volume_by_level", "Number of log entries by level"
            )

            # Error metrics
            self._error_count: Counter = Counter(
                "error_count_total", "Total number of errors"
            )
            self._error_count_by_type: Counter = Counter(
                "error_count_by_type", "Number of errors by type"
            )

            # Latency metrics
            self._log_latency: Histogram = Histogram(
                "log_latency_seconds", "Log processing latency in seconds"
            )

            # Handler metrics
            self._handler_errors: Counter = Counter(
                "handler_errors_total", "Total number of handler errors"
            )
            self._handler_latency: Histogram = Histogram(
                "handler_latency_seconds", "Handler processing latency in seconds"
            )

            # Buffer metrics
            self._buffer_size: Gauge = Gauge(
                "buffer_size_bytes", "Current buffer size in bytes"
            )
            self._buffer_usage: Gauge = Gauge(
                "buffer_usage_ratio", "Current buffer usage ratio"
            )

            self._metrics: Dict[str, Union[Counter, Gauge, Histogram]] = {
                "log_volume_total": self._log_volume,
                "log_volume_by_level": self._log_volume_by_level,
                "error_count_total": self._error_count,
                "error_count_by_type": self._error_count_by_type,
                "log_latency_seconds": self._log_latency,
                "handler_errors_total": self._handler_errors,
                "handler_latency_seconds": self._handler_latency,
                "buffer_size_bytes": self._buffer_size,
                "buffer_usage_ratio": self._buffer_usage,
            }
        except Exception as e:
            logger.exception("Error initializing log metrics: %s", e)
            raise

    def get_metric(self, name: str) -> Optional[Union[Counter, Gauge, Histogram]]:
        """Get a metric by name.

        Args:
            name: Name of the metric.

        Returns:
            Optional[Union[Counter, Gauge, Histogram]]: The metric if found.

        Raises:
            ValueError: If name is empty or None.
        """
        if not name:
            raise ValueError("Metric name cannot be empty")

        try:
            return self._metrics.get(name)
        except Exception as e:
            logger.exception("Error getting metric %s: %s", name, e)
            raise

    async def record_log(self, log_entry: Dict[str, Any], latency: float) -> None:
        """Record metrics for a log entry.

        Args:
            log_entry: The log entry that was processed.
            latency: Time taken to process the entry in seconds.

        Raises:
            ValueError: If latency is negative or log_entry is empty.
            TypeError: If log_entry is not a dict.
        """
        if not log_entry:
            raise ValueError("log_entry cannot be empty")
        if latency < 0:
            raise ValueError("latency cannot be negative")

        try:
            # Update volume metrics
            self._log_volume.inc()

            level = str(log_entry.get("level", "")).lower()
            self._log_volume_by_level.update_labels({"level": level})
            self._log_volume_by_level.inc()

            # Update error metrics
            if level in {"error", "critical"}:
                self._error_count.inc()

                if error_type := log_entry.get("error_type"):
                    self._error_count_by_type.update_labels({"type": str(error_type)})
                    self._error_count_by_type.inc()

            # Update latency metrics
            self._log_latency.observe(latency)
        except Exception as e:
            logger.exception("Error recording log metrics: %s", e)
            raise

    async def record_handler_error(self, handler_name: str, error: Exception) -> None:
        """Record a handler error.

        Args:
            handler_name: Name of the handler.
            error: The error that occurred.

        Raises:
            ValueError: If handler_name is empty.
            TypeError: If error is not an Exception.
        """
        if not handler_name:
            raise ValueError("handler_name cannot be empty")
        if not error:
            raise TypeError("error cannot be None")

        try:
            self._handler_errors.update_labels(
                {"handler": handler_name, "error": error.__class__.__name__}
            )
            self._handler_errors.inc()
        except Exception as e:
            logger.exception("Error recording handler error: %s", e)
            raise

    async def record_handler_latency(self, handler_name: str, latency: float) -> None:
        """Record handler processing latency.

        Args:
            handler_name: Name of the handler.
            latency: Time taken by the handler in seconds.

        Raises:
            ValueError: If handler_name is empty or latency is negative.
        """
        if not handler_name:
            raise ValueError("handler_name cannot be empty")
        if latency < 0:
            raise ValueError("latency cannot be negative")

        try:
            self._handler_latency.update_labels({"handler": handler_name})
            self._handler_latency.observe(latency)
        except Exception as e:
            logger.exception("Error recording handler latency: %s", e)
            raise

    async def update_buffer_metrics(self, size_bytes: int, max_size_bytes: int) -> None:
        """Update buffer metrics.

        Args:
            size_bytes: Current buffer size in bytes.
            max_size_bytes: Maximum buffer size in bytes.

        Raises:
            ValueError: If size_bytes or max_size_bytes is negative,
                or if size_bytes > max_size_bytes.
        """
        if size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        if max_size_bytes < 0:
            raise ValueError("max_size_bytes cannot be negative")
        if size_bytes > max_size_bytes:
            raise ValueError("size_bytes cannot be greater than max_size_bytes")

        try:
            self._buffer_size.set(size_bytes)
            self._buffer_usage.set(size_bytes / max_size_bytes)
        except Exception as e:
            logger.exception("Error updating buffer metrics: %s", e)
            raise

    def export(self) -> Dict[str, Union[Counter, Gauge, Histogram]]:
        """Export all metrics.

        Returns:
            Dict[str, Union[Counter, Gauge, Histogram]]: Dict mapping metric names to metrics.

        Raises:
            Exception: If there is an error exporting metrics.
        """
        try:
            return self._metrics.copy()
        except Exception as e:
            logger.exception("Error exporting metrics: %s", e)
            raise
