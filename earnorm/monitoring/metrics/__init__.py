"""Metrics module for monitoring."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Metric:
    """Base class for all metrics.

    Examples:
        >>> metric = Metric(
        ...     name="cpu_usage",
        ...     value=75.5,
        ...     description="CPU usage percentage",
        ...     tags={"host": "server1"}
        ... )
        >>> print(metric.value)  # 75.5
    """

    name: str
    value: float
    description: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "tags": self.tags,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        """Create metric from dictionary."""
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
