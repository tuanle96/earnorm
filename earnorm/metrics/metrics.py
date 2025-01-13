"""Metrics system for EarnORM."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client.registry import CollectorRegistry

from ..utils.singleton import Singleton

T = TypeVar("T")


class MetricsManager(metaclass=Singleton):
    """Manager for metrics collection."""

    def __init__(self) -> None:
        """Initialize metrics manager."""
        self.registry = CollectorRegistry()

        # Database metrics
        self.db_operations = Counter(
            "earnorm_db_operations_total",
            "Total number of database operations",
            ["operation", "collection"],
            registry=self.registry,
        )
        self.db_operation_duration = Histogram(
            "earnorm_db_operation_duration_seconds",
            "Duration of database operations",
            ["operation", "collection"],
            registry=self.registry,
        )
        self.db_connections = Gauge(
            "earnorm_db_connections",
            "Number of active database connections",
            registry=self.registry,
        )
        self.db_errors = Counter(
            "earnorm_db_errors_total",
            "Total number of database errors",
            ["operation", "collection", "error_type"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_operations = Counter(
            "earnorm_cache_operations_total",
            "Total number of cache operations",
            ["operation"],
            registry=self.registry,
        )
        self.cache_hits = Counter(
            "earnorm_cache_hits_total",
            "Total number of cache hits",
            registry=self.registry,
        )
        self.cache_misses = Counter(
            "earnorm_cache_misses_total",
            "Total number of cache misses",
            registry=self.registry,
        )
        self.cache_size = Gauge(
            "earnorm_cache_size_bytes",
            "Size of cache in bytes",
            registry=self.registry,
        )

        # Model metrics
        self.model_operations = Counter(
            "earnorm_model_operations_total",
            "Total number of model operations",
            ["operation", "model"],
            registry=self.registry,
        )
        self.model_validation_errors = Counter(
            "earnorm_model_validation_errors_total",
            "Total number of model validation errors",
            ["model", "field"],
            registry=self.registry,
        )
        self.model_instances = Gauge(
            "earnorm_model_instances",
            "Number of model instances",
            ["model"],
            registry=self.registry,
        )

        # Event metrics
        self.event_emissions = Counter(
            "earnorm_event_emissions_total",
            "Total number of event emissions",
            ["event"],
            registry=self.registry,
        )
        self.event_handler_duration = Summary(
            "earnorm_event_handler_duration_seconds",
            "Duration of event handlers",
            ["event", "handler"],
            registry=self.registry,
        )
        self.event_handler_errors = Counter(
            "earnorm_event_handler_errors_total",
            "Total number of event handler errors",
            ["event", "handler", "error_type"],
            registry=self.registry,
        )

        # Plugin metrics
        self.plugin_operations = Counter(
            "earnorm_plugin_operations_total",
            "Total number of plugin operations",
            ["operation", "plugin"],
            registry=self.registry,
        )
        self.plugin_errors = Counter(
            "earnorm_plugin_errors_total",
            "Total number of plugin errors",
            ["plugin", "error_type"],
            registry=self.registry,
        )
        self.active_plugins = Gauge(
            "earnorm_active_plugins",
            "Number of active plugins",
            registry=self.registry,
        )

    def track_db_operation(
        self, operation: str, collection: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track database operation.

        Args:
            operation: Operation name
            collection: Collection name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.monotonic()
                try:
                    result = func(*args, **kwargs)
                    self.db_operations.labels(
                        operation=operation, collection=collection
                    ).inc()
                    return result
                except Exception as e:
                    self.db_errors.labels(
                        operation=operation,
                        collection=collection,
                        error_type=type(e).__name__,
                    ).inc()
                    raise
                finally:
                    duration = time.monotonic() - start_time
                    self.db_operation_duration.labels(
                        operation=operation, collection=collection
                    ).observe(duration)

            return cast(Callable[..., T], wrapper)

        return decorator

    def track_cache_operation(
        self, operation: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track cache operation.

        Args:
            operation: Operation name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                self.cache_operations.labels(operation=operation).inc()
                return func(*args, **kwargs)

            return cast(Callable[..., T], wrapper)

        return decorator

    def track_model_operation(
        self, operation: str, model: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track model operation.

        Args:
            operation: Operation name
            model: Model name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                self.model_operations.labels(operation=operation, model=model).inc()
                return func(*args, **kwargs)

            return cast(Callable[..., T], wrapper)

        return decorator

    def track_event_handler(
        self, event: str, handler: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track event handler.

        Args:
            event: Event name
            handler: Handler name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.monotonic()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.event_handler_errors.labels(
                        event=event,
                        handler=handler,
                        error_type=type(e).__name__,
                    ).inc()
                    raise
                finally:
                    duration = time.monotonic() - start_time
                    self.event_handler_duration.labels(
                        event=event, handler=handler
                    ).observe(duration)

            return cast(Callable[..., T], wrapper)

        return decorator

    def track_plugin_operation(
        self, operation: str, plugin: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to track plugin operation.

        Args:
            operation: Operation name
            plugin: Plugin name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                try:
                    result = func(*args, **kwargs)
                    self.plugin_operations.labels(
                        operation=operation, plugin=plugin
                    ).inc()
                    return result
                except Exception as e:
                    self.plugin_errors.labels(
                        plugin=plugin, error_type=type(e).__name__
                    ).inc()
                    raise

            return cast(Callable[..., T], wrapper)

        return decorator

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits.inc()

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.cache_misses.inc()

    def set_cache_size(self, size: int) -> None:
        """Set cache size.

        Args:
            size: Cache size in bytes
        """
        self.cache_size.set(size)

    def set_db_connections(self, count: int) -> None:
        """Set number of database connections.

        Args:
            count: Number of connections
        """
        self.db_connections.set(count)

    def set_model_instances(self, model: str, count: int) -> None:
        """Set number of model instances.

        Args:
            model: Model name
            count: Number of instances
        """
        self.model_instances.labels(model=model).set(count)

    def set_active_plugins(self, count: int) -> None:
        """Set number of active plugins.

        Args:
            count: Number of plugins
        """
        self.active_plugins.set(count)

    def record_model_validation_error(self, model: str, field: str) -> None:
        """Record model validation error.

        Args:
            model: Model name
            field: Field name
        """
        self.model_validation_errors.labels(model=model, field=field).inc()

    def record_event_emission(self, event: str) -> None:
        """Record event emission.

        Args:
            event: Event name
        """
        self.event_emissions.labels(event=event).inc()
