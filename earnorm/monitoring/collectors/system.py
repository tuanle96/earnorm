"""System collector for monitoring."""

import logging
from datetime import datetime, timezone
from typing import Dict, Sequence

import psutil

from earnorm.monitoring.collectors.base import BaseCollector
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge

logger = logging.getLogger(__name__)


class SystemCollector(BaseCollector):
    """System collector for monitoring.

    Examples:
        >>> collector = SystemCollector()
        >>> metrics = await collector.collect()
        >>> for metric in metrics:
        ...     print(f"{metric.name}: {metric.value}")
        system_cpu_usage: 45.2
        system_memory_usage: 78.5
        system_disk_usage: 65.0
    """

    def __init__(self, interval: int = 60) -> None:
        """Initialize system collector.

        Args:
            interval: Collection interval in seconds.
        """
        super().__init__("system", interval)

        # Initialize metrics
        self._metrics: Dict[str, Counter | Gauge] = {
            # CPU metrics
            "system_cpu_usage": Gauge(
                "system_cpu_usage",
                "CPU usage percentage",
                {"unit": "percent"},
            ),
            "system_cpu_count": Gauge(
                "system_cpu_count",
                "Number of CPUs",
                {"type": "logical"},
            ),
            # Memory metrics
            "system_memory_usage": Gauge(
                "system_memory_usage",
                "Memory usage in bytes",
                {"unit": "bytes"},
            ),
            "system_memory_total": Gauge(
                "system_memory_total",
                "Total memory in bytes",
                {"unit": "bytes"},
            ),
            "system_memory_percent": Gauge(
                "system_memory_percent",
                "Memory usage percentage",
                {"unit": "percent"},
            ),
            # Disk metrics
            "system_disk_usage": Gauge(
                "system_disk_usage",
                "Disk usage in bytes",
                {"unit": "bytes"},
            ),
            "system_disk_total": Gauge(
                "system_disk_total",
                "Total disk space in bytes",
                {"unit": "bytes"},
            ),
            "system_disk_percent": Gauge(
                "system_disk_percent",
                "Disk usage percentage",
                {"unit": "percent"},
            ),
            # Network metrics
            "system_network_bytes_sent": Counter(
                "system_network_bytes_sent",
                "Total bytes sent",
                {"unit": "bytes"},
            ),
            "system_network_bytes_recv": Counter(
                "system_network_bytes_recv",
                "Total bytes received",
                {"unit": "bytes"},
            ),
        }

    async def collect(self) -> Sequence[Metric]:
        """Collect system metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            psutil.Error: If unable to collect system metrics.
            Exception: If any other error occurs during collection.
        """
        try:
            # CPU metrics
            self._metrics["system_cpu_usage"].set(psutil.cpu_percent(interval=1))
            self._metrics["system_cpu_count"].set(psutil.cpu_count())

            # Memory metrics
            memory = psutil.virtual_memory()
            self._metrics["system_memory_usage"].set(memory.used)
            self._metrics["system_memory_total"].set(memory.total)
            self._metrics["system_memory_percent"].set(memory.percent)

            # Disk metrics
            disk = psutil.disk_usage("/")
            self._metrics["system_disk_usage"].set(disk.used)
            self._metrics["system_disk_total"].set(disk.total)
            self._metrics["system_disk_percent"].set(disk.percent)

            # Network metrics
            net_io = psutil.net_io_counters()
            self._metrics["system_network_bytes_sent"].set(net_io.bytes_sent)
            self._metrics["system_network_bytes_recv"].set(net_io.bytes_recv)

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
        except psutil.Error as e:
            logger.error("Error collecting system metrics: %s", str(e), exc_info=True)
            raise
        except Exception:
            logger.error("Error collecting system metrics", exc_info=True)
            raise
