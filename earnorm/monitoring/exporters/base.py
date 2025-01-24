"""Base exporter for monitoring."""

from datetime import datetime
from typing import Dict, List, Optional, Sequence

from earnorm.monitoring.interfaces import ExporterInterface
from earnorm.monitoring.metrics import Metric


class BaseExporter(ExporterInterface):
    """Base exporter for monitoring.

    Examples:
        >>> class PrometheusExporter(BaseExporter):
        ...     def __init__(self, port: int = 9090) -> None:
        ...         super().__init__("prometheus")
        ...         self._port = port
        ...
        ...     async def start(self) -> None:
        ...         # Start HTTP server
        ...         pass
        ...
        ...     async def stop(self) -> None:
        ...         # Stop HTTP server
        ...         pass
        ...
        ...     async def export_metrics(
        ...         self, metrics: Sequence[Metric]
        ...     ) -> None:
        ...         # Export metrics in Prometheus format
        ...         pass
        ...
        ...     async def get_metrics(
        ...         self,
        ...         start_time: datetime,
        ...         end_time: datetime,
        ...         metrics: Optional[Sequence[str]] = None,
        ...     ) -> Dict[str, List[float]]:
        ...         # Get metrics from Prometheus
        ...         pass
    """

    def __init__(self, name: str) -> None:
        """Initialize exporter.

        Args:
            name: Exporter name.
        """
        self._name = name

    @property
    def name(self) -> str:
        """Get exporter name.

        Returns:
            Exporter name.
        """
        return self._name

    async def start(self) -> None:
        """Start exporter.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Exporter must implement start method")

    async def stop(self) -> None:
        """Stop exporter.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Exporter must implement stop method")

    async def export_metrics(self, metrics: Sequence[Metric]) -> None:
        """Export metrics.

        Args:
            metrics: List of metrics to export.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Exporter must implement export_metrics method")

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[Sequence[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics.

        Args:
            start_time: Start time.
            end_time: End time.
            metrics: List of metric names to get.

        Returns:
            Dictionary mapping metric names to lists of values.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Exporter must implement get_metrics method")
