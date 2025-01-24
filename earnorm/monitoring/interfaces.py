"""Interfaces for monitoring module."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Sequence

from earnorm.monitoring.alerts.rules import Alert
from earnorm.monitoring.metrics import Metric


class CollectorInterface(Protocol):
    """Interface for metric collectors.

    Examples:
        >>> class SystemCollector(CollectorInterface):
        ...     @property
        ...     def name(self) -> str:
        ...         return "system"
        ...
        ...     @property
        ...     def interval(self) -> int:
        ...         return 60  # Collect every minute
        ...
        ...     def should_collect(self) -> bool:
        ...         return True
        ...
        ...     async def collect(self) -> Sequence[Metric]:
        ...         # Collect system metrics
        ...         return [
        ...             Metric(name="cpu_usage", value=0.75),
        ...             Metric(name="memory_usage", value=0.85),
        ...         ]
    """

    @property
    def name(self) -> str:
        """Get collector name.

        Returns:
            Name of the collector
        """
        ...

    @property
    def interval(self) -> int:
        """Get collection interval in seconds.

        Returns:
            Collection interval in seconds
        """
        ...

    def should_collect(self) -> bool:
        """Check if collector should collect metrics.

        Returns:
            True if collector should collect metrics
        """
        ...

    async def collect(self) -> Sequence[Metric]:
        """Collect metrics.

        Returns:
            List of collected metrics
        """
        ...


class ExporterInterface(Protocol):
    """Interface for metric exporters.

    Examples:
        >>> class PrometheusExporter(ExporterInterface):
        ...     async def start(self) -> None:
        ...         # Start Prometheus HTTP server
        ...         pass
        ...
        ...     async def stop(self) -> None:
        ...         # Stop Prometheus HTTP server
        ...         pass
        ...
        ...     async def export_metrics(self, metrics: Sequence[Metric]) -> None:
        ...         # Export metrics to Prometheus
        ...         pass
        ...
        ...     async def get_metrics(
        ...         self,
        ...         start_time: datetime,
        ...         end_time: datetime,
        ...         metrics: Optional[Sequence[str]] = None,
        ...     ) -> Dict[str, Any]:
        ...         # Query metrics from Prometheus
        ...         return {"cpu_usage": [0.75, 0.80, 0.85]}
    """

    async def start(self) -> None:
        """Start exporter."""
        ...

    async def stop(self) -> None:
        """Stop exporter."""
        ...

    async def export_metrics(self, metrics: Sequence[Metric]) -> None:
        """Export metrics.

        Args:
            metrics: List of metrics to export
        """
        ...

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[Sequence[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics.

        Args:
            start_time: Start time
            end_time: End time
            metrics: Optional list of metric names to get

        Returns:
            Dictionary mapping metric names to lists of values
        """
        ...


class AlertHandlerInterface(Protocol):
    """Interface for alert handlers.

    Examples:
        >>> class AlertHandler(AlertHandlerInterface):
        ...     async def handle_alert(self, alert: Alert) -> None:
        ...         # Handle alert
        ...         pass
        ...
        ...     async def resolve_alert(self, alert: Alert) -> None:
        ...         # Resolve alert
        ...         pass
        ...
        ...     def get_active_alerts(
        ...         self,
        ...         severity: Optional[str] = None,
        ...         metric: Optional[str] = None,
        ...     ) -> List[Alert]:
        ...         # Get active alerts
        ...         return []
        ...
        ...     async def store_alert(self, alert: Alert) -> None:
        ...         # Store alert
        ...         pass
        ...
        ...     async def get_alert_history(
        ...         self,
        ...         start_time: datetime,
        ...         end_time: datetime,
        ...         metric: Optional[str] = None,
        ...         severity: Optional[str] = None,
        ...     ) -> List[Dict[str, Any]]:
        ...         # Get alert history
        ...         return []
    """

    async def handle_alert(self, alert: Alert) -> None:
        """Handle alert.

        Args:
            alert: Alert to handle
        """
        ...

    async def resolve_alert(self, alert: Alert) -> None:
        """Resolve alert.

        Args:
            alert: Alert to resolve
        """
        ...

    def get_active_alerts(
        self, severity: Optional[str] = None, metric: Optional[str] = None
    ) -> List[Alert]:
        """Get active alerts.

        Args:
            severity: Optional severity filter
            metric: Optional metric name filter

        Returns:
            List of active alerts
        """
        ...

    async def store_alert(self, alert: Alert) -> None:
        """Store alert.

        Args:
            alert: Alert to store
        """
        ...

    async def get_alert_history(
        self,
        start_time: datetime,
        end_time: datetime,
        metric: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get alert history.

        Args:
            start_time: Start time
            end_time: End time
            metric: Optional metric name filter
            severity: Optional severity filter

        Returns:
            List of alert history entries
        """
        ...


class NotificationInterface(Protocol):
    """Interface for notifications.

    Examples:
        >>> class NotificationSystem(NotificationInterface):
        ...     def add_email_channel(
        ...         self,
        ...         recipients: List[str],
        ...         severity_filter: Optional[str] = None,
        ...     ) -> None:
        ...         # Add email channel
        ...         pass
        ...
        ...     def add_slack_channel(
        ...         self,
        ...         webhook_url: str,
        ...         channel: str,
        ...         severity_filter: Optional[str] = None,
        ...     ) -> None:
        ...         # Add Slack channel
        ...         pass
        ...
        ...     def add_webhook_channel(
        ...         self,
        ...         url: str,
        ...         headers: Optional[Dict[str, str]] = None,
        ...         severity_filter: Optional[str] = None,
        ...     ) -> None:
        ...         # Add webhook channel
        ...         pass
        ...
        ...     async def send_alert(self, alert: Alert) -> None:
        ...         # Send alert notification
        ...         pass
        ...
        ...     async def send_resolution(self, alert: Alert) -> None:
        ...         # Send resolution notification
        ...         pass
    """

    def add_email_channel(
        self, recipients: List[str], severity_filter: Optional[str] = None
    ) -> None:
        """Add email channel.

        Args:
            recipients: List of email recipients
            severity_filter: Optional severity filter
        """
        ...

    def add_slack_channel(
        self, webhook_url: str, channel: str, severity_filter: Optional[str] = None
    ) -> None:
        """Add Slack channel.

        Args:
            webhook_url: Slack webhook URL
            channel: Slack channel name
            severity_filter: Optional severity filter
        """
        ...

    def add_webhook_channel(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        severity_filter: Optional[str] = None,
    ) -> None:
        """Add webhook channel.

        Args:
            url: Webhook URL
            headers: Optional HTTP headers
            severity_filter: Optional severity filter
        """
        ...

    async def send_alert(self, alert: Alert) -> None:
        """Send alert notification.

        Args:
            alert: Alert to send notification for
        """
        ...

    async def send_resolution(self, alert: Alert) -> None:
        """Send resolution notification.

        Args:
            alert: Alert to send resolution notification for
        """
        ...


class MonitorLifecycleInterface(Protocol):
    """Interface for monitor lifecycle.

    Examples:
        >>> class MonitorLifecycleManager(MonitorLifecycleInterface):
        ...     async def init(self, **config: Any) -> None:
        ...         # Initialize monitoring
        ...         pass
        ...
        ...     async def start(self) -> None:
        ...         # Start monitoring
        ...         pass
        ...
        ...     async def stop(self) -> None:
        ...         # Stop monitoring
        ...         pass
        ...
        ...     async def get_metrics(
        ...         self,
        ...         start_time: datetime,
        ...         end_time: datetime,
        ...         metrics: Optional[List[str]] = None,
        ...     ) -> Dict[str, List[float]]:
        ...         # Get metrics
        ...         return {"cpu_usage": [0.75, 0.80, 0.85]}
    """

    async def init(self, **config: Any) -> None:
        """Initialize monitoring.

        Args:
            **config: Configuration options
        """
        ...

    async def start(self) -> None:
        """Start monitoring."""
        ...

    async def stop(self) -> None:
        """Stop monitoring."""
        ...

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics.

        Args:
            start_time: Start time
            end_time: End time
            metrics: Optional list of metric names to get

        Returns:
            Dictionary mapping metric names to lists of values
        """
        ...
