"""Base metrics implementation."""

from typing import Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class MetricProtocol(Protocol):
    """Protocol for metrics."""

    @property
    def name(self) -> str:
        """Get metric name."""
        ...

    @property
    def description(self) -> str:
        """Get metric description."""
        ...

    @property
    def value(self) -> float:
        """Get metric value."""
        ...

    @property
    def labels(self) -> Dict[str, str]:
        """Get metric labels."""
        ...

    def set(self, value: float) -> None:
        """Set metric value.

        Args:
            value: Value to set
        """
        ...

    def update_labels(self, labels: Dict[str, str]) -> None:
        """Update metric labels.

        Args:
            labels: Labels to update
        """
        ...


@runtime_checkable
class CounterProtocol(MetricProtocol, Protocol):
    """Protocol for counter metrics."""

    def inc(self, value: float = 1) -> None:
        """Increment counter value.

        Args:
            value: Value to increment by
        """
        ...


@runtime_checkable
class GaugeProtocol(MetricProtocol, Protocol):
    """Protocol for gauge metrics."""

    def set(self, value: float) -> None:
        """Set gauge value.

        Args:
            value: Value to set
        """
        ...


@runtime_checkable
class HistogramProtocol(MetricProtocol, Protocol):
    """Protocol for histogram metrics."""

    def observe(self, value: float) -> None:
        """Observe value.

        Args:
            value: Value to observe
        """
        ...


class BaseMetric:
    """Base class for metrics."""

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize base metric.

        Args:
            name: Metric name
            description: Metric description
            labels: Optional metric labels
        """
        self._name = name
        self._description = description
        self._labels = labels or {}
        self._value: float = 0.0

    @property
    def name(self) -> str:
        """Get metric name."""
        return self._name

    @property
    def description(self) -> str:
        """Get metric description."""
        return self._description

    @property
    def value(self) -> float:
        """Get metric value."""
        return self._value

    @property
    def labels(self) -> Dict[str, str]:
        """Get metric labels."""
        return self._labels

    def set(self, value: float) -> None:
        """Set metric value.

        Args:
            value: Value to set
        """
        self._value = value

    def update_labels(self, labels: Dict[str, str]) -> None:
        """Update metric labels.

        Args:
            labels: Labels to update
        """
        self._labels.update(labels)


class Counter(BaseMetric):
    """Counter metric.

    Examples:
        >>> counter = Counter("requests_total", "Total requests")
        >>> counter.inc()
        >>> counter.value
        1.0
        >>> counter.inc(2)
        >>> counter.value
        3.0
    """

    def inc(self, value: float = 1) -> None:
        """Increment counter value.

        Args:
            value: Value to increment by
        """
        self._value += value


class Gauge(BaseMetric):
    """Gauge metric.

    Examples:
        >>> gauge = Gauge("cpu_usage", "CPU usage")
        >>> gauge.set(0.75)
        >>> gauge.value
        0.75
    """


class Histogram(BaseMetric):
    """Histogram metric.

    Examples:
        >>> histogram = Histogram("response_time", "Response time")
        >>> histogram.observe(0.1)
        >>> histogram.value
        0.1
    """

    def observe(self, value: float) -> None:
        """Observe value.

        Args:
            value: Value to observe
        """
        self._value = value
