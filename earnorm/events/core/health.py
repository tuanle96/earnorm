"""Health check implementation.

This module provides health checking for the event system.
It monitors the health of event bus, backends, and handlers.

Features:
- Connection health checks
- Backend status monitoring
- Handler health checks
- Metrics collection
- Health status reporting

Examples:
    ```python
    from earnorm.events.core.health import HealthChecker

    # Create health checker
    checker = HealthChecker(event_bus)

    # Check health
    status = await checker.check()
    print(f"Event system health: {status}")

    # Get detailed health report
    report = await checker.get_report()
    print(f"Health report: {report}")
    ```
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from earnorm.events.core.bus import EventBus
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status data class.

    Attributes:
        healthy: Whether the system is healthy
        timestamp: When the check was performed
        details: Detailed health information
        error: Optional error message
    """

    healthy: bool
    timestamp: datetime
    details: Dict[str, Any]
    error: Optional[str] = None


class HealthChecker:
    """Health checker for event system.

    This class provides health checking functionality for the event system.
    It monitors the health of event bus, backends, and handlers.

    Attributes:
        event_bus: Event bus instance to monitor
        check_interval: How often to run checks in seconds
        timeout: Maximum time for checks in seconds

    Examples:
        ```python
        # Create health checker
        checker = HealthChecker(
            event_bus,
            check_interval=60.0,
            timeout=5.0
        )

        # Start health checks
        await checker.start()

        # Get current health
        status = await checker.check()
        print(f"Health: {status}")

        # Stop health checks
        await checker.stop()
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        check_interval: float = 60.0,
        timeout: float = 5.0,
    ) -> None:
        """Initialize health checker.

        Args:
            event_bus: Event bus instance to monitor
            check_interval: How often to run checks in seconds
            timeout: Maximum time for checks in seconds
        """
        self.event_bus = event_bus
        self.check_interval = check_interval
        self.timeout = timeout
        self._task: Optional[asyncio.Task[None]] = None
        self._last_status: Optional[HealthStatus] = None

    async def start(self) -> None:
        """Start health checking.

        This starts periodic health checks in the background.
        """
        if self._task is not None:
            return

        self._task = asyncio.create_task(self._run_checks())
        logger.info("Started health checking")

    async def stop(self) -> None:
        """Stop health checking.

        This stops the background health checks.
        """
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Stopped health checking")

    async def check(self) -> HealthStatus:
        """Run health check.

        This performs a health check of the event system.

        Returns:
            HealthStatus with check results
        """
        try:
            # Check backend connection
            backend_status = await self._check_backend()

            # Check handler registry
            handler_status = await self._check_handlers()

            # Check event bus
            bus_status = await self._check_bus()

            # Combine results
            details = {
                "backend": backend_status,
                "handlers": handler_status,
                "bus": bus_status,
            }

            status = HealthStatus(
                healthy=all(
                    s.get("healthy", False)
                    for s in [backend_status, handler_status, bus_status]
                ),
                timestamp=datetime.now(timezone.utc),
                details=details,
            )

        except Exception as e:
            status = HealthStatus(
                healthy=False,
                timestamp=datetime.now(timezone.utc),
                details={},
                error=str(e),
            )

        self._last_status = status
        return status

    async def get_report(self) -> Dict[str, Any]:
        """Get health report.

        This returns a detailed health report including:
        - Overall health status
        - Backend connection status
        - Handler health
        - Event bus status
        - Recent errors
        - Performance metrics

        Returns:
            Dict with health report data
        """
        status = await self.check()

        return {
            "healthy": status.healthy,
            "timestamp": status.timestamp.isoformat(),
            "details": status.details,
            "error": status.error,
            "metrics": await self._get_metrics(),
        }

    async def _run_checks(self) -> None:
        """Run periodic health checks."""
        while True:
            try:
                await self.check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check failed: %s", str(e))
                await asyncio.sleep(self.check_interval)

    async def _check_backend(self) -> Dict[str, Any]:
        """Check backend health.

        Returns:
            Dict containing:
                healthy (bool): Whether backend is healthy
                latency (float): Connection latency in seconds
                error (str, optional): Error message if unhealthy
        """
        try:
            # Check connection
            await asyncio.wait_for(
                self.event_bus.backend.ping(),  # type: ignore
                timeout=self.timeout,
            )

            return {
                "healthy": True,
                "latency": 0.0,  # TODO: Measure latency
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _check_handlers(self) -> Dict[str, Any]:
        """Check handler health.

        Returns:
            Dict containing:
                healthy (bool): Whether all handlers are healthy
                total (int): Total number of handlers
                errors (List[str]): List of handler errors
        """
        handlers = list(self.event_bus.handlers)  # type: ignore
        total = len(handlers)  # type: ignore
        errors: List[str] = []

        for handler in handlers:  # type: ignore
            try:
                # Basic handler check
                if not isinstance(handler, EventHandler):  # type: ignore
                    errors.append("Invalid handler: %s" % str(handler))  # type: ignore
            except Exception as e:
                errors.append(str(e))

        return {
            "healthy": len(errors) == 0,
            "total": total,
            "errors": errors,
        }

    async def _check_bus(self) -> Dict[str, Any]:
        """Check event bus health.

        Returns:
            Dict containing:
                healthy (bool): Whether bus is healthy
                error (str, optional): Error message if unhealthy
        """
        try:
            # Check if bus is running
            if not self.event_bus.is_running:  # type: ignore
                return {
                    "healthy": False,
                    "error": "Event bus is not running",
                }

            return {
                "healthy": True,
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    async def _get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dict containing performance metrics
        """
        return {
            "uptime": 0.0,  # TODO: Track uptime
            "events_processed": 0,  # TODO: Track events
            "errors": 0,  # TODO: Track errors
        }
