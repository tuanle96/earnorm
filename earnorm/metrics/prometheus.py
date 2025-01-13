"""Prometheus metrics implementation."""

import time
from abc import ABCMeta
from typing import Any, Dict, Optional

from prometheus_client import Counter, Histogram
from prometheus_client.registry import CollectorRegistry

from ..utils.singleton import Singleton
from .base import MetricsManager


class SingletonABCMeta(Singleton, ABCMeta):
    """Metaclass combining Singleton and ABCMeta."""

    pass


class PrometheusMetrics(MetricsManager, metaclass=SingletonABCMeta):
    """Prometheus metrics implementation."""

    def __init__(self) -> None:
        """Initialize metrics manager."""
        self.registry = CollectorRegistry()

        # Validation metrics
        self.validation_total = Counter(
            "earnorm_validation_total",
            "Total number of validations",
            ["model", "field", "validator", "success"],
            registry=self.registry,
        )

        # Event metrics
        self.event_total = Counter(
            "earnorm_event_total",
            "Total number of events",
            ["event", "model", "success"],
            registry=self.registry,
        )

        # Access metrics
        self.access_total = Counter(
            "earnorm_access_total",
            "Total number of access checks",
            ["model", "operation", "success"],
            registry=self.registry,
        )

        # Database metrics
        self.db_operations = Counter(
            "earnorm_db_operations_total",
            "Total number of database operations",
            ["operation", "collection", "success"],
            registry=self.registry,
        )
        self.db_operation_duration = Histogram(
            "earnorm_db_operation_duration_seconds",
            "Duration of database operations",
            ["operation", "collection"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_operations = Counter(
            "earnorm_cache_operations_total",
            "Total number of cache operations",
            ["operation", "hit"],
            registry=self.registry,
        )

    async def track_validation(
        self,
        model: str,
        field: str,
        validator: str,
        value: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track validation result."""
        self.validation_total.labels(
            model=model,
            field=field,
            validator=validator,
            success=str(success).lower(),
        ).inc()

    async def track_event(
        self,
        event: str,
        model: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track event."""
        self.event_total.labels(
            event=event,
            model=model,
            success=str(success).lower(),
        ).inc()

    async def track_access_granted(
        self,
        user_id: str,
        model: str,
        operation: str,
    ) -> None:
        """Track access granted."""
        self.access_total.labels(
            model=model,
            operation=operation,
            success="true",
        ).inc()

    async def track_access_denied(
        self,
        user_id: str,
        model: str,
        operation: str,
        reason: str,
    ) -> None:
        """Track access denied."""
        self.access_total.labels(
            model=model,
            operation=operation,
            success="false",
        ).inc()

    async def track_db_operation(
        self,
        operation: str,
        collection: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track database operation."""
        self.db_operations.labels(
            operation=operation,
            collection=collection,
            success=str(success).lower(),
        ).inc()
        self.db_operation_duration.labels(
            operation=operation,
            collection=collection,
        ).observe(duration)

    async def track_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool = False,
    ) -> None:
        """Track cache operation."""
        self.cache_operations.labels(
            operation=operation,
            hit=str(hit).lower(),
        ).inc()

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get metrics.

        Note: Prometheus metrics are pull-based, so this method returns
        the current registry state without filtering.
        """
        return {
            "registry": self.registry,
            "timestamp": time.time(),
        }


# Global metrics manager instance
metrics_manager = PrometheusMetrics()
