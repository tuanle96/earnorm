"""Health checking utilities."""

import logging
from typing import Any, Dict, Optional

from earnorm.pool.core.pool import ConnectionPool

logger = logging.getLogger(__name__)


class HealthChecker:
    """Connection pool health checker."""

    def __init__(
        self,
        pool: ConnectionPool,
        check_interval: float = 60.0,
        max_failures: int = 3,
    ) -> None:
        """Initialize health checker.

        Args:
            pool: Connection pool to check
            check_interval: Interval between checks in seconds
            max_failures: Maximum consecutive failures before marking unhealthy
        """
        self.pool = pool
        self.check_interval = check_interval
        self.max_failures = max_failures
        self._failures = 0
        self._last_check: Optional[float] = None
        self._metrics: Dict[str, Any] = {}

    async def check_health(self) -> bool:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        try:
            # Get connection
            conn = await self.pool.acquire()
            try:
                # Ping connection
                is_healthy = await conn.ping()
                if is_healthy:
                    self._failures = 0
                    self._update_metrics(healthy=True)
                    return True
                else:
                    self._failures += 1
                    self._update_metrics(healthy=False)
                    return False
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error("Health check failed: %s", e)
            self._failures += 1
            self._update_metrics(healthy=False)
            return False

    @property
    def is_healthy(self) -> bool:
        """Check if pool is considered healthy.

        Returns:
            True if pool is healthy
        """
        return self._failures < self.max_failures

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get health check metrics.

        Returns:
            Dict of metrics
        """
        return self._metrics.copy()

    def _update_metrics(self, healthy: bool) -> None:
        """Update health check metrics.

        Args:
            healthy: Whether check was successful
        """
        self._metrics.update(
            {
                "failures": self._failures,
                "max_failures": self.max_failures,
                "is_healthy": self.is_healthy,
                "last_check_healthy": healthy,
                "pool_size": self.pool.size,
                "pool_active": self.pool.active,
                "pool_available": self.pool.available,
            }
        )
