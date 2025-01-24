"""Monitoring module for EarnORM.

This module provides monitoring functionality for EarnORM, including:
- Metric collection from various sources (system, Redis, network, etc.)
- Metric export to different formats (Prometheus, etc.)
- Alert handling and notifications
- Lifecycle management for monitoring components
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from earnorm.monitoring.collectors.base import BaseCollector
from earnorm.monitoring.exporters.base import BaseExporter
from earnorm.monitoring.interfaces import (
    AlertHandlerInterface,
    CollectorInterface,
    ExporterInterface,
)
from earnorm.monitoring.lifecycle import MonitorLifecycleManager
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge, Histogram

# Global monitor instance
_monitor: Optional[MonitorLifecycleManager] = None

__all__ = [
    # Base classes
    "BaseCollector",
    "BaseExporter",
    # Metric types
    "Counter",
    "Gauge",
    "Histogram",
    "Metric",
    # Functions
    "init_monitor",
    "stop_monitor",
    "get_metrics",
]


async def init_monitor(
    collectors: Optional[Sequence[CollectorInterface]] = None,
    exporters: Optional[Sequence[ExporterInterface]] = None,
    alert_handler: Optional[AlertHandlerInterface] = None,
    **config: Any,
) -> None:
    """Initialize monitoring.

    Args:
        collectors: List of collectors to use.
        exporters: List of exporters to use.
        alert_handler: Alert handler to use.
        **config: Additional configuration options.

    Raises:
        Exception: If unable to initialize monitoring.

    Examples:
        >>> from earnorm.monitoring import init_monitor
        >>> from earnorm.monitoring.collectors import SystemCollector
        >>> from earnorm.monitoring.exporters import PrometheusExporter
        >>> from earnorm.monitoring.alerts import AlertHandler
        >>>
        >>> await init_monitor(
        ...     collectors=[SystemCollector()],
        ...     exporters=[PrometheusExporter()],
        ...     alert_handler=AlertHandler(),
        ... )
    """
    global _monitor

    if _monitor is not None:
        await _monitor.stop()

    _monitor = MonitorLifecycleManager()
    await _monitor.init(
        collectors=list(collectors or []),
        exporters=list(exporters or []),
        alert_handler=alert_handler,
        **config,
    )
    await _monitor.start()


async def stop_monitor() -> None:
    """Stop monitoring.

    Raises:
        Exception: If unable to stop monitoring.

    Examples:
        >>> from earnorm.monitoring import stop_monitor
        >>> await stop_monitor()
    """
    global _monitor

    if _monitor is not None:
        await _monitor.stop()
        _monitor = None


async def get_metrics(
    start_time: datetime,
    end_time: datetime,
    metrics: Optional[List[str]] = None,
) -> Dict[str, List[float]]:
    """Get metrics.

    Args:
        start_time: Start time to get metrics from.
        end_time: End time to get metrics until.
        metrics: List of metric names to get.

    Returns:
        Dictionary mapping metric names to lists of values.

    Raises:
        Exception: If unable to get metrics.

    Examples:
        >>> from earnorm.monitoring import get_metrics
        >>> from datetime import datetime, timedelta
        >>>
        >>> end = datetime.now()
        >>> start = end - timedelta(hours=1)
        >>> metrics = await get_metrics(
        ...     start_time=start,
        ...     end_time=end,
        ...     metrics=["cpu_usage", "memory_usage"],
        ... )
    """
    if _monitor is None:
        return {}

    return await _monitor.get_metrics(start_time, end_time, metrics)
