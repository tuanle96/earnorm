"""Database collector for monitoring."""

import logging
from datetime import datetime, timezone
from typing import Dict, Sequence, cast

from earnorm.di import container
from earnorm.monitoring.collectors.base import BaseCollector
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge
from earnorm.pool import MongoPool
from earnorm.pool.protocols.connection import ConnectionProtocol

logger = logging.getLogger(__name__)


class DatabaseCollector(BaseCollector):
    """Database collector for monitoring.

    Examples:
        >>> collector = DatabaseCollector()
        >>> metrics = await collector.collect()
        >>> for metric in metrics:
        ...     print(f"{metric.name}: {metric.value}")
        database_connections_active: 25
        database_operations_total: 150
        database_latency_seconds: 0.05
    """

    def __init__(self, interval: int = 30) -> None:
        """Initialize database collector.

        Args:
            interval: Collection interval in seconds.
        """
        super().__init__("database", interval)

        # Initialize metrics
        self._metrics: Dict[str, Counter | Gauge] = {
            # Connection metrics
            "database_connections_active": Gauge(
                "database_connections_active",
                "Number of active database connections",
                {"type": "active"},
            ),
            "database_connections_available": Gauge(
                "database_connections_available",
                "Number of available database connections",
                {"type": "available"},
            ),
            "database_connections_max": Gauge(
                "database_connections_max",
                "Maximum number of database connections",
                {"type": "max"},
            ),
            # Operation metrics
            "database_operations_total": Counter(
                "database_operations_total",
                "Total number of database operations",
                {"type": "total"},
            ),
            "database_operations_query": Counter(
                "database_operations_query",
                "Number of query operations",
                {"type": "query"},
            ),
            "database_operations_insert": Counter(
                "database_operations_insert",
                "Number of insert operations",
                {"type": "insert"},
            ),
            "database_operations_update": Counter(
                "database_operations_update",
                "Number of update operations",
                {"type": "update"},
            ),
            "database_operations_delete": Counter(
                "database_operations_delete",
                "Number of delete operations",
                {"type": "delete"},
            ),
            # Error metrics
            "database_errors_total": Counter(
                "database_errors_total",
                "Total number of database errors",
                {"type": "total"},
            ),
            # Latency metrics
            "database_latency": Gauge(
                "database_latency",
                "Database operation latency in seconds",
                {"unit": "seconds"},
            ),
        }

    async def collect(self) -> Sequence[Metric]:
        """Collect database metrics.

        Returns:
            Sequence[Metric]: List of collected metrics.

        Raises:
            Exception: If unable to collect database metrics.
        """
        try:
            pool = cast(MongoPool, await container.get("mongo_pool"))

            # Connection metrics
            gauge = cast(Gauge, self._metrics["database_connections_active"])
            gauge.set(float(pool.size - pool.available))

            gauge = cast(Gauge, self._metrics["database_connections_available"])
            gauge.set(float(pool.available))

            gauge = cast(Gauge, self._metrics["database_connections_max"])
            gauge.set(float(pool.max_size))

            # Get database stats
            conn: ConnectionProtocol = await pool.acquire()
            try:
                stats = await conn.execute("admin", "serverStatus")
                opcounters = cast(Dict[str, int], stats.get("opcounters", {}))

                # Operation metrics
                counter = cast(Counter, self._metrics["database_operations_total"])
                counter.set(float(sum(opcounters.values())))

                counter = cast(Counter, self._metrics["database_operations_query"])
                counter.set(float(opcounters.get("query", 0)))

                counter = cast(Counter, self._metrics["database_operations_insert"])
                counter.set(float(opcounters.get("insert", 0)))

                counter = cast(Counter, self._metrics["database_operations_update"])
                counter.set(float(opcounters.get("update", 0)))

                counter = cast(Counter, self._metrics["database_operations_delete"])
                counter.set(float(opcounters.get("delete", 0)))

                # Error metrics
                errors = cast(Dict[str, int], stats.get("errors", {}))
                counter = cast(Counter, self._metrics["database_errors_total"])
                counter.set(float(errors.get("total", 0)))

                # Latency metrics
                latencies = cast(Dict[str, float], stats.get("opLatencies", {}))
                latency = (
                    float(latencies.get("latency", 0)) / 1000
                )  # Convert to seconds
                gauge = cast(Gauge, self._metrics["database_latency"])
                gauge.set(latency)
            finally:
                await pool.release(conn)

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
            logger.error("Error collecting database metrics", exc_info=True)
            raise
