"""Lifecycle manager for monitoring."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, cast

from earnorm.monitoring.interfaces import (
    AlertHandlerInterface,
    CollectorInterface,
    ExporterInterface,
    MonitorLifecycleInterface,
)
from earnorm.monitoring.metrics import Metric

logger = logging.getLogger(__name__)


class MonitorConfig(TypedDict, total=False):
    """Monitor configuration."""

    collectors: List[CollectorInterface]
    exporters: List[ExporterInterface]
    alert_handler: Optional[AlertHandlerInterface]


class MonitorLifecycleManager(MonitorLifecycleInterface):
    """Lifecycle manager for monitoring."""

    def __init__(self) -> None:
        """Initialize monitor lifecycle manager."""
        self._collectors: List[CollectorInterface] = []
        self._exporters: List[ExporterInterface] = []
        self._alert_handler: Optional[AlertHandlerInterface] = None
        self._collection_task: Optional[asyncio.Task[None]] = None
        self._is_running: bool = False

    async def init(self, **config: Any) -> None:
        """Initialize monitoring.

        Args:
            **config: Configuration options.
                - collectors: List of collectors to use.
                - exporters: List of exporters to use.
                - alert_handler: Alert handler to use.

        Examples:
            >>> await monitor.init(
            ...     collectors=[SystemCollector(), DatabaseCollector()],
            ...     exporters=[PrometheusExporter(), InfluxDBExporter()],
            ...     alert_handler=AlertHandler(),
            ... )
        """
        monitor_config = cast(MonitorConfig, config)
        self._collectors = monitor_config.get("collectors", [])
        self._exporters = monitor_config.get("exporters", [])
        self._alert_handler = monitor_config.get("alert_handler")

    async def start(self) -> None:
        """Start monitoring.

        Examples:
            >>> await monitor.start()

        Raises:
            Exception: If starting exporters fails
        """
        if self._is_running:
            return

        self._is_running = True

        # Start exporters
        for exporter in self._exporters:
            try:
                await exporter.start()
            except Exception as e:
                logger.error(f"Failed to start exporter: {e}")
                self._is_running = False
                raise

        # Start collection task
        self._collection_task = asyncio.create_task(self._collect_metrics())

    async def stop(self) -> None:
        """Stop monitoring.

        Examples:
            >>> await monitor.stop()

        Raises:
            Exception: If stopping exporters fails
        """
        if not self._is_running:
            return

        self._is_running = False

        # Stop collection task
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping collection task: {e}")

        # Stop exporters
        for exporter in self._exporters:
            try:
                await exporter.stop()
            except Exception as e:
                logger.error(f"Failed to stop exporter: {e}")
                raise

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics.

        Args:
            start_time: Start time.
            end_time: End time.
            metrics: List of metric names to get.

        Returns:
            Dictionary mapping metric names to values.

        Examples:
            >>> metrics = await monitor.get_metrics(
            ...     start_time=datetime(2024, 1, 1),
            ...     end_time=datetime(2024, 1, 2),
            ...     metrics=["cpu_usage", "memory_usage"],
            ... )
        """
        results: Dict[str, List[float]] = {}
        for exporter in self._exporters:
            try:
                metrics_data = await exporter.get_metrics(start_time, end_time, metrics)
                results.update(metrics_data)
            except Exception as e:
                logger.error(f"Failed to get metrics from exporter: {e}")
        return results

    async def _collect_metrics(self) -> None:
        """Collect metrics from collectors and export them."""
        while self._is_running:
            try:
                # Get metrics from collectors that should collect
                metrics: List[Metric] = []
                for collector in self._collectors:
                    if collector.should_collect():
                        try:
                            collector_metrics = await collector.collect()
                            metrics.extend(collector_metrics)
                        except Exception as e:
                            # Log error and continue
                            logger.error(
                                f"Error collecting metrics from {collector.name}: {e}"
                            )

                # Export metrics
                for exporter in self._exporters:
                    try:
                        await exporter.export_metrics(metrics)
                    except Exception as e:
                        # Log error and continue
                        logger.error(f"Error exporting metrics: {e}")

                # Sleep until next collection
                min_interval = min(
                    (c.interval for c in self._collectors if c.should_collect()),
                    default=60,
                )
                await asyncio.sleep(min_interval)
            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                break
            except Exception as e:
                # Log error and continue
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
