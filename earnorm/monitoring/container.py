"""Dependency injection container for monitoring module."""

from dependency_injector.providers import Configuration, Dependency, Factory, Singleton

from earnorm.di import Container
from earnorm.events.core import EventBus
from earnorm.pool.config import PoolConfig

from .alerts.handlers import AlertHandler
from .collectors.network_collector import NetworkCollector
from .collectors.redis_collector import RedisCollector
from .exporters.prometheus_exporter import PrometheusExporter
from .pools import MetricsPool, NotificationPool


class MonitoringContainer(Container):
    """DI container for monitoring module.

    This container provides dependencies for the monitoring module, including:
    - Metrics and notification pools
    - Event bus for metric collection and alerts
    - Collectors for Redis and network metrics
    - Prometheus exporter for metrics
    - Alert handler for processing and sending notifications

    Examples:
        >>> container = MonitoringContainer()
        >>> container.init_resources()
        >>> redis_collector = container.redis_collector()
        >>> metrics = await redis_collector.collect()

        >>> # Configure pools
        >>> container.config.metrics.pool.min_size = 5
        >>> container.config.metrics.pool.max_size = 20
        >>> container.config.notifications.pool.min_size = 2
        >>> container.config.notifications.pool.max_size = 10

        >>> # Get metrics pool
        >>> metrics_pool = container.metrics_pool()
        >>> await metrics_pool.init()

        >>> # Get alert handler
        >>> alert_handler = container.alert_handler()
        >>> await alert_handler.handle_alert(alert)
    """

    # Configuration
    config: Configuration = Configuration()
    """Container configuration provider.

    This provider allows configuring various aspects of the monitoring module:
    - Metrics pool settings (min_size, max_size, max_idle_time, connection_timeout)
    - Notification pool settings (min_size, max_size, max_idle_time, connection_timeout)
    """

    # Pools
    metrics_pool: Singleton[MetricsPool] = Singleton(
        MetricsPool,
        config=Factory(
            PoolConfig,
            min_size=config.metrics.pool.min_size,
            max_size=config.metrics.pool.max_size,
            max_idle_time=config.metrics.pool.max_idle_time,
            connection_timeout=config.metrics.pool.connection_timeout,
        ),
    )
    """Metrics pool singleton provider.

    This pool is used for storing and retrieving metrics data. It is configured using
    the settings from config.metrics.pool.
    """

    notification_pool: Singleton[NotificationPool] = Singleton(
        NotificationPool,
        config=Factory(
            PoolConfig,
            min_size=config.notifications.pool.min_size,
            max_size=config.notifications.pool.max_size,
            max_idle_time=config.notifications.pool.max_idle_time,
            connection_timeout=config.notifications.pool.connection_timeout,
        ),
    )
    """Notification pool singleton provider.

    This pool is used for sending notifications. It is configured using
    the settings from config.notifications.pool.
    """

    # Event bus
    event_bus: Singleton[EventBus] = Singleton(EventBus)
    """Event bus singleton provider.

    This event bus is used for:
    - Publishing metric collection events
    - Publishing alert events
    - Handling metric and alert notifications
    """

    # Collectors
    redis_collector: Factory[RedisCollector] = Factory(
        RedisCollector, pool=Dependency(), event_bus=event_bus
    )
    """Redis collector factory provider.

    This collector gathers metrics from Redis instances. It requires:
    - A Redis connection pool (injected as a dependency)
    - The event bus for publishing metric events
    """

    network_collector: Factory[NetworkCollector] = Factory(
        NetworkCollector, event_bus=event_bus
    )
    """Network collector factory provider.

    This collector gathers network metrics. It requires:
    - The event bus for publishing metric events
    """

    # Exporters
    prometheus_exporter: Factory[PrometheusExporter] = Factory(
        PrometheusExporter, metrics_pool=metrics_pool
    )
    """Prometheus exporter factory provider.

    This exporter converts metrics to Prometheus format. It requires:
    - The metrics pool for storing and retrieving metrics
    """

    # Alert handlers
    alert_handler: Factory[AlertHandler] = Factory(
        AlertHandler, notification_pool=notification_pool, event_bus=event_bus
    )
    """Alert handler factory provider.

    This handler processes alerts and sends notifications. It requires:
    - The notification pool for sending notifications
    - The event bus for publishing alert events
    """
