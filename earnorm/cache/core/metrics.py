"""Cache metrics collection.

This module provides metrics collection and monitoring for the cache system:
- Hit/miss rates
- Error rates
- Operation timing
- Total operations

Examples:
    ```python
    from earnorm.cache.core.metrics import MetricsCollector

    # Create collector
    collector = MetricsCollector()

    # Record operations
    collector.start_operation()
    try:
        value = await cache.get("key")
        if value is not None:
            collector.record_hit()
        else:
            collector.record_miss()
    except Exception:
        collector.record_error()

    # Get metrics
    metrics = collector.metrics
    print(f"Hit rate: {metrics.hit_rate * 100}%")
    print(f"Average time: {metrics.average_time}ms")
    ```
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheMetrics:
    """Cache metrics data.

    This class holds cache operation metrics and provides methods to
    calculate derived metrics like hit rates and averages.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        errors: Number of errors
        total_operations: Total number of operations
        total_time: Total operation time in seconds

    Examples:
        ```python
        metrics = CacheMetrics(
            hits=100,
            misses=20,
            errors=5,
            total_operations=125,
            total_time=0.5
        )
        print(f"Hit rate: {metrics.hit_rate * 100}%")
        ```
    """

    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_operations: int = 0
    total_time: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            float: Hit rate as a ratio (0.0 to 1.0)
        """
        if self.total_operations == 0:
            return 0.0
        return self.hits / self.total_operations

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate.

        Returns:
            float: Miss rate as a ratio (0.0 to 1.0)
        """
        if self.total_operations == 0:
            return 0.0
        return self.misses / self.total_operations

    @property
    def error_rate(self) -> float:
        """Calculate cache error rate.

        Returns:
            float: Error rate as a ratio (0.0 to 1.0)
        """
        if self.total_operations == 0:
            return 0.0
        return self.errors / self.total_operations

    @property
    def average_time(self) -> float:
        """Calculate average operation time.

        Returns:
            float: Average time per operation in seconds
        """
        if self.total_operations == 0:
            return 0.0
        return self.total_time / self.total_operations

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dict.

        Returns:
            Dict containing all metrics with formatted values:
            - hits: Number of hits
            - misses: Number of misses
            - errors: Number of errors
            - total_operations: Total operations
            - total_time: Total time in seconds (rounded to 3 decimals)
            - hit_rate: Hit rate as percentage (rounded to 2 decimals)
            - miss_rate: Miss rate as percentage (rounded to 2 decimals)
            - error_rate: Error rate as percentage (rounded to 2 decimals)
            - average_time: Average time in milliseconds (rounded to 2 decimals)
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_operations": self.total_operations,
            "total_time": round(self.total_time, 3),
            "hit_rate": round(self.hit_rate * 100, 2),
            "miss_rate": round(self.miss_rate * 100, 2),
            "error_rate": round(self.error_rate * 100, 2),
            "average_time": round(self.average_time * 1000, 2),  # ms
        }


class MetricsCollector:
    """Cache metrics collector.

    This class collects and aggregates cache operation metrics.
    It tracks hits, misses, errors, and operation timing.

    Examples:
        ```python
        collector = MetricsCollector()

        # Record cache hit
        collector.start_operation()
        collector.record_hit()

        # Record cache miss
        collector.start_operation()
        collector.record_miss()

        # Get current metrics
        metrics = collector.metrics
        print(f"Hit rate: {metrics.hit_rate * 100}%")
        ```
    """

    def __init__(self) -> None:
        """Initialize collector with empty metrics."""
        self._metrics = CacheMetrics()
        self._start_time: Optional[float] = None

    def start_operation(self) -> None:
        """Start timing cache operation.

        This method should be called before each cache operation
        to track operation timing.
        """
        self._start_time = time.time()

    def record_hit(self) -> None:
        """Record cache hit.

        This method should be called when a cache lookup succeeds.
        It increments the hit counter and records operation timing.
        """
        self._metrics.hits += 1
        self._record_operation()

    def record_miss(self) -> None:
        """Record cache miss.

        This method should be called when a cache lookup fails.
        It increments the miss counter and records operation timing.
        """
        self._metrics.misses += 1
        self._record_operation()

    def record_error(self) -> None:
        """Record cache error.

        This method should be called when a cache operation fails.
        It increments the error counter and records operation timing.
        """
        self._metrics.errors += 1
        self._record_operation()

    def _record_operation(self) -> None:
        """Record operation timing.

        This internal method updates total operation count and time.
        It should be called after recording a hit, miss, or error.
        """
        if self._start_time is not None:
            self._metrics.total_time += time.time() - self._start_time
            self._metrics.total_operations += 1
            self._start_time = None

    def reset(self) -> None:
        """Reset metrics.

        This method clears all metrics and timing data.
        """
        self._metrics = CacheMetrics()
        self._start_time = None

    @property
    def metrics(self) -> CacheMetrics:
        """Get current metrics.

        Returns:
            CacheMetrics: Current metrics snapshot
        """
        return self._metrics
