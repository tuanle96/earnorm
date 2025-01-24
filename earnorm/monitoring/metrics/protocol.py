from typing import Dict, Protocol, runtime_checkable


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


@runtime_checkable
class CounterProtocol(MetricProtocol, Protocol):
    """Protocol for counter metrics."""

    def inc(self, value: float = 1) -> None:
        """Increment counter value.

        Args:
            value: Value to increment by
        """
        ...

    def set(self, value: float) -> None:
        """Set counter value.

        Args:
            value: Value to set
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

    def set(self, value: float) -> None:
        """Set histogram value.

        Args:
            value: Value to set
        """
        ...
