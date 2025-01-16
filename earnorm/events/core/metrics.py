"""Metrics collection implementation.

This module provides metrics collection for the event system.
It tracks various metrics about event processing and system health.

Features:
- Event counts
- Processing times
- Error rates
- Handler metrics
- Backend metrics
- System health

Examples:
    ```python
    from earnorm.events.core.metrics import MetricsCollector

    # Create metrics collector
    collector = MetricsCollector(event_bus)

    # Get current metrics
    metrics = await collector.get_metrics()
    print("Event metrics: %s" % metrics)

    # Get detailed report
    report = await collector.get_report()
    print("Metrics report: %s" % report)
    ```
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from earnorm.events.core.bus import EventBus
from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)


@dataclass
class EventMetrics:
    """Event metrics data class.

    Attributes:
        total_events: Total events processed
        success_count: Successfully processed events
        error_count: Failed events
        processing_times: List of processing times
        start_time: When collection started
        last_event: When last event was processed
    """

    total_events: int = 0
    success_count: int = 0
    error_count: int = 0
    processing_times: List[float] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_event: Optional[datetime] = None

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_events == 0:
            return 0.0
        return self.error_count / self.total_events

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_events == 0:
            return 0.0
        return self.success_count / self.total_events

    @property
    def average_time(self) -> float:
        """Calculate average processing time."""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)

    @property
    def uptime(self) -> float:
        """Calculate uptime in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


class MetricsCollector:
    """Metrics collector for event system.

    This class collects and tracks metrics about the event system.
    It provides insights into event processing and system health.

    Attributes:
        event_bus: Event bus instance to monitor
        max_samples: Maximum number of timing samples to keep
        metrics: Current event metrics

    Examples:
        ```python
        # Create collector
        collector = MetricsCollector(
            event_bus,
            max_samples=1000
        )

        # Record event
        await collector.record_event(event, success=True, time=0.5)

        # Get metrics
        metrics = await collector.get_metrics()
        print(f"Success rate: {metrics.success_rate}")
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        max_samples: int = 1000,
    ) -> None:
        """Initialize metrics collector.

        Args:
            event_bus: Event bus instance to monitor
            max_samples: Maximum number of timing samples
        """
        self.event_bus = event_bus
        self.max_samples = max_samples
        self.metrics = EventMetrics()

    async def record_event(
        self,
        event: Event,
        success: bool,
        time: Optional[float] = None,
    ) -> None:
        """Record event metrics.

        This records metrics about an event that was processed.

        Args:
            event: Event that was processed
            success: Whether processing succeeded
            time: Processing time in seconds
        """
        self.metrics.total_events += 1
        if success:
            self.metrics.success_count += 1
        else:
            self.metrics.error_count += 1

        if time is not None:
            self.metrics.processing_times.append(time)
            if len(self.metrics.processing_times) > self.max_samples:
                self.metrics.processing_times.pop(0)

        self.metrics.last_event = datetime.now(timezone.utc)

    async def get_metrics(self) -> EventMetrics:
        """Get current metrics.

        Returns:
            Current event metrics
        """
        return self.metrics

    async def get_report(self) -> Dict[str, Any]:
        """Get detailed metrics report.

        This returns a detailed report including:
        - Event counts and rates
        - Processing times
        - Handler metrics
        - Backend metrics
        - System metrics

        Returns:
            Dict with metrics data
        """
        metrics = await self.get_metrics()

        return {
            "events": {
                "total": metrics.total_events,
                "success": metrics.success_count,
                "errors": metrics.error_count,
                "success_rate": metrics.success_rate,
                "error_rate": metrics.error_rate,
                "avg_time": metrics.average_time,
            },
            "handlers": await self._get_handler_metrics(),
            "backend": await self._get_backend_metrics(),
            "system": {
                "uptime": metrics.uptime,
                "start_time": metrics.start_time.isoformat(),
                "last_event": (
                    metrics.last_event.isoformat() if metrics.last_event else None
                ),
            },
        }

    async def _get_handler_metrics(self) -> Dict[str, Any]:
        """Get handler metrics."""
        handlers = self.event_bus.handlers  # type: ignore
        patterns = self.event_bus.patterns  # type: ignore
        return {
            "total": len(handlers),  # type: ignore
            "patterns": len(patterns),  # type: ignore
            # TODO: Add per-handler metrics
        }

    async def _get_backend_metrics(self) -> Dict[str, Any]:
        """Get backend metrics."""
        try:
            # Basic connection check
            start = time.monotonic()
            await self.event_bus.backend.ping()  # type: ignore
            latency = time.monotonic() - start

            return {
                "connected": True,
                "latency": latency,
                # TODO: Add more backend metrics
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
            }
