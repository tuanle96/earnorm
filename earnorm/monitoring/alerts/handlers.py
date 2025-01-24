"""Handlers module for monitoring alerts."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, cast

from earnorm.monitoring.alerts.notifications import NotificationSystem
from earnorm.monitoring.alerts.rules import Alert
from earnorm.pool.factory import PoolFactory
from earnorm.pool.protocols import ConnectionProtocol


class AlertHandler:
    """
    Handler for processing and managing alerts.

    Examples:
        >>> handler = AlertHandler()
        >>> alert = Alert(
        ...     name="High CPU Usage",
        ...     metric="cpu_usage",
        ...     value=85.5,
        ...     threshold=80,
        ...     severity="warning"
        ... )
        >>> await handler.handle_alert(alert)
    """

    def __init__(self):
        """Initialize the alert handler."""
        self.notification_system = NotificationSystem()
        self._active_alerts: Dict[str, Alert] = {}
        self._resolved_alerts: Set[str] = set()
        self._last_notification: Dict[str, datetime] = {}

    def _get_alert_key(self, alert: Alert) -> str:
        """Generate unique key for alert."""
        return f"{alert.metric}:{alert.severity}:{sorted(alert.tags.items())}"

    def _should_notify(self, alert: Alert) -> bool:
        """Check if notification should be sent."""
        key = self._get_alert_key(alert)

        # Check if alert is already active
        if key in self._active_alerts:
            last_notification = self._last_notification.get(key)
            if last_notification:
                # Check notification interval based on severity
                interval = {
                    "critical": timedelta(minutes=5),
                    "warning": timedelta(minutes=15),
                    "info": timedelta(minutes=30),
                }.get(alert.severity, timedelta(minutes=15))

                if datetime.now(timezone.utc) - last_notification < interval:
                    return False

        return True

    async def handle_alert(self, alert: Alert) -> None:
        """
        Handle an alert.

        Args:
            alert: Alert to handle
        """
        key = self._get_alert_key(alert)

        # Check if alert is new or updated
        is_new = key not in self._active_alerts
        is_updated = not is_new and alert.value != self._active_alerts[key].value

        if is_new or is_updated:
            # Store alert
            self._active_alerts[key] = alert

            # Send notification if needed
            if self._should_notify(alert):
                await self.notification_system.send_alert(alert)
                self._last_notification[key] = datetime.now(timezone.utc)

    async def resolve_alert(self, alert: Alert) -> None:
        """
        Resolve an alert.

        Args:
            alert: Alert to resolve
        """
        key = self._get_alert_key(alert)

        if key in self._active_alerts:
            # Remove from active alerts
            del self._active_alerts[key]

            # Add to resolved alerts
            self._resolved_alerts.add(key)

            # Send resolution notification
            await self.notification_system.send_resolution(alert)

    def get_active_alerts(
        self, severity: Optional[str] = None, metric: Optional[str] = None
    ) -> List[Alert]:
        """
        Get active alerts with optional filtering.

        Args:
            severity: Optional severity filter
            metric: Optional metric name filter

        Returns:
            List of active alerts
        """
        alerts = list(self._active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if metric:
            alerts = [a for a in alerts if a.metric == metric]

        return sorted(
            alerts,
            key=lambda a: (
                {"critical": 0, "warning": 1, "info": 2}.get(a.severity, 3),
                a.timestamp,
            ),
        )

    async def store_alert(self, alert: Alert) -> None:
        """
        Store alert in database.

        Args:
            alert: Alert to store
        """
        pool = await PoolFactory.create_mongo_pool(
            uri="mongodb://localhost:27017", database="earnbase"
        )
        conn = cast(ConnectionProtocol, pool)
        collection = conn.get_collection("alerts")

        # Store alert
        await collection.insert_one(alert.to_dict())

        # Update alert history
        history = {
            "metric": alert.metric,
            "severity": alert.severity,
            "value": alert.value,
            "threshold": alert.threshold,
            "tags": alert.tags,
            "timestamp": alert.timestamp,
        }

        await collection.update_one(
            {"metric": alert.metric, "severity": alert.severity, "tags": alert.tags},
            {
                "$push": {
                    "history": {
                        "$each": [history],
                        "$slice": -100,  # Keep last 100 entries
                    }
                }
            },
            upsert=True,
        )

    async def get_alert_history(
        self,
        start_time: datetime,
        end_time: datetime,
        metric: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get alert history from database.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric: Optional metric name filter
            severity: Optional severity filter

        Returns:
            List of alert history entries
        """
        pool = await PoolFactory.create_mongo_pool(
            uri="mongodb://localhost:27017", database="earnbase"
        )
        conn = cast(ConnectionProtocol, pool)
        collection = conn.get_collection("alerts")

        # Build query
        query: Dict[str, Any] = {"timestamp": {"$gte": start_time, "$lte": end_time}}

        if metric:
            query["metric"] = metric
        if severity:
            query["severity"] = severity

        # Get alert history
        cursor = collection.find(query).sort("timestamp", -1)

        history: List[Dict[str, Any]] = []
        async for doc in cursor:
            history.append(doc)

        return history
