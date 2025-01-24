"""Redis metrics collector."""

import logging
from datetime import datetime, timezone
from typing import Dict, Sequence, cast

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.collectors import BaseCollector
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge
from earnorm.pool import RedisPool
from earnorm.pool.protocols.connection import ConnectionProtocol

logger = logging.getLogger(__name__)


class RedisCollector(BaseCollector):
    """Redis collector for monitoring.

    Examples:
        >>> collector = RedisCollector()
        >>> metrics = await collector.collect()
        >>> for metric in metrics:
        ...     print(f"{metric.name}: {metric.value}")
        redis_connected_clients: 25
        redis_used_memory_bytes: 1024576
        redis_commands_processed: 150
    """

    def __init__(
        self, pool: RedisPool, event_bus: EventBus, interval: int = 30
    ) -> None:
        """Initialize Redis collector.

        Args:
            pool: Redis connection pool
            event_bus: Event bus for emitting metrics
            interval: Collection interval in seconds
        """
        super().__init__("redis", interval)
        self._pool = pool
        self._event_bus = event_bus

        # Initialize metrics
        self._metrics: Dict[str, Counter | Gauge] = {
            # Client metrics
            "redis_connected_clients": Gauge(
                "redis_connected_clients",
                "Number of client connections",
                {"type": "connected"},
            ),
            "redis_blocked_clients": Gauge(
                "redis_blocked_clients",
                "Number of blocked clients",
                {"type": "blocked"},
            ),
            # Memory metrics
            "redis_used_memory_bytes": Gauge(
                "redis_used_memory_bytes",
                "Used memory in bytes",
                {"unit": "bytes"},
            ),
            "redis_used_memory_peak_bytes": Gauge(
                "redis_used_memory_peak_bytes",
                "Peak memory usage in bytes",
                {"unit": "bytes"},
            ),
            "redis_memory_fragmentation_ratio": Gauge(
                "redis_memory_fragmentation_ratio",
                "Memory fragmentation ratio",
                {"type": "ratio"},
            ),
            # Command metrics
            "redis_commands_processed": Counter(
                "redis_commands_processed",
                "Total commands processed",
                {"type": "total"},
            ),
            "redis_commands_per_sec": Gauge(
                "redis_commands_per_sec",
                "Commands processed per second",
                {"unit": "per_second"},
            ),
            # Key metrics
            "redis_total_keys": Gauge(
                "redis_total_keys",
                "Total number of keys",
                {"type": "total"},
            ),
            "redis_expired_keys": Counter(
                "redis_expired_keys",
                "Total expired keys",
                {"type": "expired"},
            ),
            "redis_evicted_keys": Counter(
                "redis_evicted_keys",
                "Total evicted keys",
                {"type": "evicted"},
            ),
            # Network metrics
            "redis_total_connections_received": Counter(
                "redis_total_connections_received",
                "Total connections received",
                {"type": "received"},
            ),
            "redis_total_net_input_bytes": Counter(
                "redis_total_net_input_bytes",
                "Total network input in bytes",
                {"unit": "bytes"},
            ),
            "redis_total_net_output_bytes": Counter(
                "redis_total_net_output_bytes",
                "Total network output in bytes",
                {"unit": "bytes"},
            ),
        }

    async def collect(self) -> Sequence[Metric]:
        """Collect Redis metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            Exception: If any error occurs during collection.
        """
        try:
            conn: ConnectionProtocol = await self._pool.acquire()
            try:
                # Get Redis info
                info: str = await conn.execute("INFO")
                info_dict = self._parse_info(info)

                # Client metrics
                gauge = cast(Gauge, self._metrics["redis_connected_clients"])
                gauge.set(float(info_dict.get("connected_clients", 0)))

                gauge = cast(Gauge, self._metrics["redis_blocked_clients"])
                gauge.set(float(info_dict.get("blocked_clients", 0)))

                # Memory metrics
                gauge = cast(Gauge, self._metrics["redis_used_memory_bytes"])
                gauge.set(float(info_dict.get("used_memory", 0)))

                gauge = cast(Gauge, self._metrics["redis_used_memory_peak_bytes"])
                gauge.set(float(info_dict.get("used_memory_peak", 0)))

                gauge = cast(Gauge, self._metrics["redis_memory_fragmentation_ratio"])
                gauge.set(float(info_dict.get("mem_fragmentation_ratio", 0)))

                # Command metrics
                counter = cast(Counter, self._metrics["redis_commands_processed"])
                counter.set(float(info_dict.get("total_commands_processed", 0)))

                gauge = cast(Gauge, self._metrics["redis_commands_per_sec"])
                gauge.set(float(info_dict.get("instantaneous_ops_per_sec", 0)))

                # Key metrics
                total_keys = sum(
                    int(info_dict.get(f"db{i}", "").split(",")[0].split("=")[1])
                    for i in range(16)
                    if f"db{i}" in info_dict
                )
                gauge = cast(Gauge, self._metrics["redis_total_keys"])
                gauge.set(float(total_keys))

                counter = cast(Counter, self._metrics["redis_expired_keys"])
                counter.set(float(info_dict.get("expired_keys", 0)))

                counter = cast(Counter, self._metrics["redis_evicted_keys"])
                counter.set(float(info_dict.get("evicted_keys", 0)))

                # Network metrics
                counter = cast(
                    Counter, self._metrics["redis_total_connections_received"]
                )
                counter.set(float(info_dict.get("total_connections_received", 0)))

                counter = cast(Counter, self._metrics["redis_total_net_input_bytes"])
                counter.set(float(info_dict.get("total_net_input_bytes", 0)))

                counter = cast(Counter, self._metrics["redis_total_net_output_bytes"])
                counter.set(float(info_dict.get("total_net_output_bytes", 0)))

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
            finally:
                await conn.close()
        except Exception:
            logger.exception("Error collecting Redis metrics")
            raise

    def _parse_info(self, info: str) -> Dict[str, str]:
        """Parse Redis INFO command output.

        Args:
            info: Redis INFO command output

        Returns:
            Dict[str, str]: Dictionary mapping Redis info keys to values
        """
        result: Dict[str, str] = {}
        for line in info.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
