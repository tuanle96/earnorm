"""Events for monitoring module."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from earnorm.events import Event
from earnorm.monitoring.alerts.rules import Alert
from earnorm.monitoring.metrics import Metric


@dataclass
class MetricCollectedEvent(Event):
    """Event emitted when metrics are collected.

    Examples:
        >>> metrics: List[Metric] = [Metric(name="cpu_usage", value=0.75)]
        >>> event = MetricCollectedEvent(
        ...     metrics=metrics,
        ...     collector_name="system",
        ...     timestamp=1234567890.0,
        ...     metadata={"source": "system_collector"}
        ... )
        >>> await event_bus.emit(event)
    """

    metrics: List[Metric]
    collector_name: str
    timestamp: float
    metadata: Optional[Dict[str, str]] = None


@dataclass
class AlertTriggeredEvent(Event):
    """Event emitted when an alert is triggered.

    Examples:
        >>> alert: Alert = Alert(
        ...     name="high_cpu",
        ...     severity="critical",
        ...     metric="cpu_usage",
        ...     value=0.95,
        ...     rule_id="cpu_threshold"
        ... )
        >>> event = AlertTriggeredEvent(
        ...     alert=alert,
        ...     timestamp=1234567890.0,
        ...     metadata={"source": "alert_handler"}
        ... )
        >>> await event_bus.emit(event)
    """

    alert: Alert
    timestamp: float
    metadata: Optional[Dict[str, str]] = None


@dataclass
class AlertResolvedEvent(Event):
    """Event emitted when an alert is resolved.

    Examples:
        >>> alert: Alert = Alert(
        ...     name="high_cpu",
        ...     severity="critical",
        ...     metric="cpu_usage",
        ...     value=0.75,
        ...     rule_id="cpu_threshold"
        ... )
        >>> event = AlertResolvedEvent(
        ...     alert=alert,
        ...     resolution_time=1234567890.0,
        ...     duration=300,  # 5 minutes
        ...     metadata={"source": "alert_handler"}
        ... )
        >>> await event_bus.emit(event)
    """

    alert: Alert
    resolution_time: float
    duration: float  # Duration in seconds
    metadata: Optional[Dict[str, str]] = None
