"""Health checks for monitoring logging health."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class HealthCheckProtocol(Protocol):
    """Protocol for health check handlers."""

    def check_health(self) -> List[str]:
        """Check handler health.

        Returns:
            List[str]: List of health issues.
        """
        ...


class LogHealth:
    """Class for monitoring logging health.

    This class provides functionality to:
    - Monitor log throughput
    - Track error rates
    - Check handler health
    - Monitor buffer usage
    - Track latency

    Examples:
        >>> # Check overall health
        >>> health = LogHealth()
        >>> status = await health.check()
        >>> print(f'Healthy: {status["healthy"]}')
        >>> print(f'Issues: {status["issues"]}')

        >>> # Monitor throughput
        >>> health = LogHealth(
        ...     min_throughput=100,  # logs/minute
        ...     max_throughput=1000  # logs/minute
        ... )
        >>> status = await health.check()
        >>> print(f'Current throughput: {status["throughput"]}')

        >>> # Track error rates
        >>> health = LogHealth(max_error_rate=0.01)  # 1%
        >>> status = await health.check()
        >>> print(f'Error rate: {status["error_rate"]}')

        >>> # Monitor latency
        >>> health = LogHealth(max_latency=0.1)  # 100ms
        >>> status = await health.check()
        >>> print(f'P95 latency: {status["p95_latency"]}')
    """

    def __init__(
        self,
        min_throughput: Optional[float] = None,
        max_throughput: Optional[float] = None,
        max_error_rate: Optional[float] = None,
        max_latency: Optional[float] = None,
        window_size: int = 60,  # 1 minute
        handlers: Optional[List[HealthCheckProtocol]] = None,
    ):
        """Initialize the log health monitor.

        Args:
            min_throughput: Minimum logs per minute.
            max_throughput: Maximum logs per minute.
            max_error_rate: Maximum error rate (0.0 to 1.0).
            max_latency: Maximum P95 latency in seconds.
            window_size: Size of monitoring window in seconds.
            handlers: List of handlers to monitor.

        Raises:
            ValueError: If any of the parameters are invalid:
                - min_throughput is negative
                - max_throughput is less than min_throughput
                - max_error_rate is not between 0 and 1
                - max_latency is negative
                - window_size is not positive
        """
        # Validate parameters
        if min_throughput is not None and min_throughput < 0:
            raise ValueError("min_throughput must be non-negative")
        if max_throughput is not None:
            if max_throughput < 0:
                raise ValueError("max_throughput must be non-negative")
            if min_throughput is not None and max_throughput < min_throughput:
                raise ValueError("max_throughput must be >= min_throughput")
        if max_error_rate is not None and not 0 <= max_error_rate <= 1:
            raise ValueError("max_error_rate must be between 0 and 1")
        if max_latency is not None and max_latency < 0:
            raise ValueError("max_latency must be non-negative")
        if window_size <= 0:
            raise ValueError("window_size must be positive")

        self.min_throughput = min_throughput
        self.max_throughput = max_throughput
        self.max_error_rate = max_error_rate
        self.max_latency = max_latency
        self.window_size = window_size
        self.handlers = handlers or []

        self._logs: List[Tuple[datetime, Dict[str, Any]]] = []
        self._latencies: List[float] = []

    def _cleanup_old_data(self) -> None:
        """Remove data outside the monitoring window."""
        try:
            cutoff = datetime.now() - timedelta(seconds=self.window_size)

            # Clean up logs
            while self._logs and self._logs[0][0] < cutoff:
                self._logs.pop(0)

            # Clean up latencies
            self._latencies = self._latencies[-1000:]  # Keep last 1000
        except Exception as e:
            logger.exception("Error cleaning up old data: %s", e)
            raise

    def _calculate_throughput(self) -> float:
        """Calculate current throughput in logs per minute.

        Returns:
            float: Current throughput.

        Raises:
            ZeroDivisionError: If there are no logs or all logs have the same timestamp.
        """
        try:
            if not self._logs:
                return 0.0

            # Get time range
            start_time = self._logs[0][0]
            end_time = self._logs[-1][0]
            duration = (end_time - start_time).total_seconds()

            if duration <= 0:
                return 0.0

            return len(self._logs) * 60.0 / duration
        except Exception as e:
            logger.exception("Error calculating throughput: %s", e)
            raise

    def _calculate_error_rate(self) -> float:
        """Calculate current error rate.

        Returns:
            float: Current error rate.

        Raises:
            ZeroDivisionError: If there are no logs.
        """
        try:
            if not self._logs:
                return 0.0

            error_count = sum(
                1
                for _, log in self._logs
                if str(log.get("level", "")).lower() in {"error", "critical"}
            )

            return error_count / len(self._logs)
        except Exception as e:
            logger.exception("Error calculating error rate: %s", e)
            raise

    def _calculate_p95_latency(self) -> float:
        """Calculate P95 latency in seconds.

        Returns:
            float: P95 latency.

        Raises:
            IndexError: If there are no latency samples.
        """
        try:
            if not self._latencies:
                return 0.0

            sorted_latencies = sorted(self._latencies)
            index = int(len(sorted_latencies) * 0.95)
            return sorted_latencies[index]
        except Exception as e:
            logger.exception("Error calculating P95 latency: %s", e)
            raise

    def _check_handler_health(self) -> List[str]:
        """Check health of all handlers.

        Returns:
            List[str]: List of handler issues.

        Raises:
            AttributeError: If a handler does not implement check_health.
            Exception: If a handler's health check fails.
        """
        issues: List[str] = []

        for handler in self.handlers:
            try:
                handler_issues = handler.check_health()
                if isinstance(handler_issues, list):  # type: ignore
                    issues.extend(handler_issues)
            except Exception as e:
                error_msg = f"Handler {handler.__class__.__name__} health check failed: {str(e)}"
                logger.exception(error_msg)
                issues.append(error_msg)

        return issues

    async def record(self, log_entry: Dict[str, Any], latency: float) -> None:
        """Record a log entry and its processing latency.

        Args:
            log_entry: The log entry that was processed.
            latency: Time taken to process the entry in seconds.

        Raises:
            ValueError: If latency is negative.
            TypeError: If log_entry is not a dict.
        """
        if not isinstance(log_entry, dict):  # type: ignore
            raise TypeError("log_entry must be a dict")
        if latency < 0:
            raise ValueError("latency must be non-negative")

        try:
            self._logs.append((datetime.now(), log_entry))
            self._latencies.append(latency)
            self._cleanup_old_data()
        except Exception as e:
            logger.exception("Error recording log entry: %s", e)
            raise

    async def check(self) -> Dict[str, Any]:
        """Check logging health.

        Returns:
            Dict[str, Any]: Health status including:
                - healthy: bool
                - issues: List[str]
                - throughput: float
                - error_rate: float
                - p95_latency: float

        Raises:
            Exception: If any health check fails.
        """
        try:
            issues: List[str] = []

            # Check throughput
            throughput = self._calculate_throughput()
            if self.min_throughput and throughput < self.min_throughput:
                issues.append(
                    f"Throughput ({throughput:.1f}/min) below "
                    f"minimum ({self.min_throughput:.1f}/min)"
                )
            if self.max_throughput and throughput > self.max_throughput:
                issues.append(
                    f"Throughput ({throughput:.1f}/min) above "
                    f"maximum ({self.max_throughput:.1f}/min)"
                )

            # Check error rate
            error_rate = self._calculate_error_rate()
            if self.max_error_rate and error_rate > self.max_error_rate:
                issues.append(
                    f"Error rate ({error_rate:.1%}) above "
                    f"maximum ({self.max_error_rate:.1%})"
                )

            # Check latency
            p95_latency = self._calculate_p95_latency()
            if self.max_latency and p95_latency > self.max_latency:
                issues.append(
                    f"P95 latency ({p95_latency:.3f}s) above "
                    f"maximum ({self.max_latency:.3f}s)"
                )

            # Check handlers
            issues.extend(self._check_handler_health())

            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "throughput": throughput,
                "error_rate": error_rate,
                "p95_latency": p95_latency,
            }
        except Exception as e:
            logger.exception("Error checking health: %s", e)
            raise
