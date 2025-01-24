"""Rules module for monitoring alerts."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from earnorm.monitoring.metrics import Metric


@dataclass
class Alert:
    """
    Alert data class.

    Examples:
        >>> alert = Alert(
        ...     name="High CPU Usage",
        ...     metric="cpu_usage",
        ...     value=85.5,
        ...     threshold=80,
        ...     severity="warning",
        ...     description="CPU usage exceeds 80%"
        ... )
        >>> print(alert.severity)  # warning
    """

    name: str
    metric: str
    value: float
    threshold: float
    severity: str
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "name": self.name,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "description": self.description,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create alert from dictionary."""
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class AlertRule:
    """
    Alert rule data class.

    Examples:
        >>> rule = AlertRule(
        ...     metric="memory_usage",
        ...     threshold=90,
        ...     duration=300,
        ...     severity="critical"
        ... )
        >>> metrics = [
        ...     Metric("memory_usage", 95.5)
        ... ]
        >>> alert = await rule.evaluate(metrics)
        >>> print(alert.severity)  # critical
    """

    metric: str
    threshold: float
    duration: int = 300  # seconds
    severity: str = "warning"
    description_template: str = field(default="")
    tags_filter: Dict[str, str] = field(default_factory=dict)
    _last_trigger: Optional[datetime] = field(default=None, init=False)
    _violation_start: Optional[datetime] = field(default=None, init=False)

    def __post_init__(self):
        """Set default description template."""
        if not self.description_template:
            self.description_template = (
                f"{self.metric} exceeds {self.threshold} "
                f"for {self.duration} seconds"
            )

    def _check_tags(self, metric: Metric) -> bool:
        """Check if metric tags match filter."""
        return all(metric.tags.get(k) == v for k, v in self.tags_filter.items())

    async def evaluate(self, metrics: Sequence[Metric]) -> Optional[Alert]:
        """
        Evaluate metrics against rule.

        Args:
            metrics: List of metrics to evaluate

        Returns:
            Alert if rule is violated, None otherwise
        """
        now = datetime.now(timezone.utc)

        # Find matching metrics
        matching = [m for m in metrics if m.name == self.metric and self._check_tags(m)]

        if not matching:
            self._violation_start = None
            return None

        # Check if any metric exceeds threshold
        violated = any(m.value > self.threshold for m in matching)

        if violated:
            # Start tracking violation
            if self._violation_start is None:
                self._violation_start = now

            # Check duration
            if (now - self._violation_start).total_seconds() >= self.duration:
                # Create alert if not triggered recently
                if (
                    self._last_trigger is None
                    or (now - self._last_trigger).total_seconds() >= self.duration
                ):
                    self._last_trigger = now

                    # Use highest value for alert
                    max_metric = max(matching, key=lambda m: m.value)
                    return Alert(
                        name=f"High {self.metric}",
                        metric=self.metric,
                        value=max_metric.value,
                        threshold=self.threshold,
                        severity=self.severity,
                        description=self.description_template,
                        tags=max_metric.tags,
                        timestamp=now,
                    )
        else:
            self._violation_start = None

        return None

    async def create_alert(self, metrics: Sequence[Metric]) -> Optional[Alert]:
        """
        Create alert from metrics if rule is violated.

        Args:
            metrics: List of metrics to evaluate

        Returns:
            Alert if rule is violated, None otherwise
        """
        return await self.evaluate(metrics)
