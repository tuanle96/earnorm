"""Network metrics collector."""

import logging
from datetime import datetime, timezone
from typing import Dict, Sequence, cast

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.collectors import BaseCollector
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge

logger = logging.getLogger(__name__)


class NetworkCollector(BaseCollector):
    """Network collector for monitoring.

    Examples:
        >>> collector = NetworkCollector()
        >>> metrics = await collector.collect()
        >>> for metric in metrics:
        ...     print(f"{metric.name}: {metric.value}")
        network_bytes_sent: 1024576
        network_bytes_received: 512000
        network_packets_sent: 1000
    """

    def __init__(self, event_bus: EventBus, interval: int = 30) -> None:
        """Initialize network collector.

        Args:
            event_bus: Event bus for emitting metrics
            interval: Collection interval in seconds
        """
        super().__init__("network", interval)
        self._event_bus = event_bus

        # Initialize metrics
        self._metrics: Dict[str, Counter | Gauge] = {
            # Bytes metrics
            "network_bytes_sent": Counter(
                "network_bytes_sent",
                "Total bytes sent",
                {"unit": "bytes"},
            ),
            "network_bytes_received": Counter(
                "network_bytes_received",
                "Total bytes received",
                {"unit": "bytes"},
            ),
            # Packets metrics
            "network_packets_sent": Counter(
                "network_packets_sent",
                "Total packets sent",
                {"type": "sent"},
            ),
            "network_packets_received": Counter(
                "network_packets_received",
                "Total packets received",
                {"type": "received"},
            ),
            # Errors metrics
            "network_errors_in": Counter(
                "network_errors_in",
                "Total input errors",
                {"type": "input"},
            ),
            "network_errors_out": Counter(
                "network_errors_out",
                "Total output errors",
                {"type": "output"},
            ),
            # Drops metrics
            "network_drops_in": Counter(
                "network_drops_in",
                "Total input drops",
                {"type": "input"},
            ),
            "network_drops_out": Counter(
                "network_drops_out",
                "Total output drops",
                {"type": "output"},
            ),
            # Interface metrics
            "network_interface_speed": Gauge(
                "network_interface_speed",
                "Interface speed in Mbps",
                {"unit": "mbps"},
            ),
            "network_interface_mtu": Gauge(
                "network_interface_mtu",
                "Interface MTU in bytes",
                {"unit": "bytes"},
            ),
        }

    async def collect(self) -> Sequence[Metric]:
        """Collect network metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            IOError: If unable to read network statistics files.
            ValueError: If unable to parse network statistics.
            Exception: If any other error occurs during collection.
        """
        try:
            # Read network stats from /proc/net/dev
            with open("/proc/net/dev") as f:
                lines = f.readlines()[2:]  # Skip header lines

            for line in lines:
                interface, stats = line.split(":")
                interface = interface.strip()
                if interface == "lo":  # Skip loopback
                    continue

                stats = [int(x) for x in stats.split()]

                # Update metrics
                counter = cast(Counter, self._metrics["network_bytes_received"])
                counter.set(float(stats[0]))

                counter = cast(Counter, self._metrics["network_packets_received"])
                counter.set(float(stats[1]))

                counter = cast(Counter, self._metrics["network_errors_in"])
                counter.set(float(stats[2]))

                counter = cast(Counter, self._metrics["network_drops_in"])
                counter.set(float(stats[3]))

                counter = cast(Counter, self._metrics["network_bytes_sent"])
                counter.set(float(stats[8]))

                counter = cast(Counter, self._metrics["network_packets_sent"])
                counter.set(float(stats[9]))

                counter = cast(Counter, self._metrics["network_errors_out"])
                counter.set(float(stats[10]))

                counter = cast(Counter, self._metrics["network_drops_out"])
                counter.set(float(stats[11]))

                # Get interface speed and MTU
                try:
                    with open(f"/sys/class/net/{interface}/speed") as f:
                        speed = int(f.read().strip())
                        gauge = cast(Gauge, self._metrics["network_interface_speed"])
                        gauge.set(float(speed))
                except (IOError, ValueError) as e:
                    logger.warning("Failed to read interface speed", exc_info=e)

                try:
                    with open(f"/sys/class/net/{interface}/mtu") as f:
                        mtu = int(f.read().strip())
                        gauge = cast(Gauge, self._metrics["network_interface_mtu"])
                        gauge.set(float(mtu))
                except (IOError, ValueError) as e:
                    logger.warning("Failed to read interface MTU", exc_info=e)

            # Emit metrics collected event
            event = Event(
                name="metrics.collected",
                data={
                    "collector": self.name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metrics": [
                        {
                            "name": metric.name,
                            "value": metric.value,
                            "labels": metric.labels,
                        }
                        for metric in self._metrics.values()
                    ],
                },
            )
            await self._event_bus.publish(event)

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
            logger.exception("Error collecting network metrics")
            raise
