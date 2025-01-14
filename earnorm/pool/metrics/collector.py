"""Pool metrics collection."""

import time
from typing import Any, Dict, List, Optional

from earnorm.pool.core.pool import ConnectionPool


class MetricsCollector:
    """Connection pool metrics collector."""

    def __init__(self, pool: ConnectionPool) -> None:
        """Initialize metrics collector.

        Args:
            pool: Connection pool to collect metrics from
        """
        self.pool = pool
        self._metrics: Dict[str, Any] = {}
        self._samples: List[Dict[str, Any]] = []
        self._max_samples = 100
        self._last_collect: Optional[float] = None

    def collect(self) -> Dict[str, Any]:
        """Collect current metrics.

        Returns:
            Dict of metrics
        """
        now = time.time()
        metrics = {
            "timestamp": now,
            "pool_size": self.pool.size,
            "pool_active": self.pool.active,
            "pool_available": self.pool.available,
            "pool_min_size": self.pool.min_size,
            "pool_max_size": self.pool.max_size,
        }

        # Add to samples
        self._samples.append(metrics)
        if len(self._samples) > self._max_samples:
            self._samples.pop(0)

        # Update metrics
        self._metrics = self._calculate_metrics()
        self._last_collect = now

        return self._metrics

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get current metrics.

        Returns:
            Dict of metrics
        """
        return self._metrics.copy()

    @property
    def samples(self) -> List[Dict[str, Any]]:
        """Get metric samples.

        Returns:
            List of metric samples
        """
        return self._samples.copy()

    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregate metrics from samples.

        Returns:
            Dict of calculated metrics
        """
        if not self._samples:
            return {}

        # Calculate stats
        sizes = [s["pool_size"] for s in self._samples]
        active = [s["pool_active"] for s in self._samples]
        available = [s["pool_available"] for s in self._samples]

        return {
            "current_size": self.pool.size,
            "current_active": self.pool.active,
            "current_available": self.pool.available,
            "avg_size": sum(sizes) / len(sizes),
            "max_size": max(sizes),
            "min_size": min(sizes),
            "avg_active": sum(active) / len(active),
            "max_active": max(active),
            "min_active": min(active),
            "avg_available": sum(available) / len(available),
            "max_available": max(available),
            "min_available": min(available),
            "samples": len(self._samples),
            "last_collect": self._last_collect,
        }
