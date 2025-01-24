"""Prometheus metrics exporter."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Type, Union, cast

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.exporters import BaseExporter
from earnorm.monitoring.metrics import Metric
from earnorm.monitoring.metrics.base import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

MetricType = Union[Counter, Gauge, Histogram]


class PrometheusExporter(BaseExporter):
    """Prometheus metrics exporter.

    Examples:
        >>> exporter = PrometheusExporter()
        >>> metrics = [
        ...     Counter("requests_total", "Total requests", value=100),
        ...     Gauge("cpu_usage", "CPU usage", value=0.75),
        ...     Histogram("response_time", "Response time", value=0.1),
        ... ]
        >>> formatted = exporter.format_metrics(metrics)
        >>> print(formatted)
        # HELP requests_total Total requests
        # TYPE requests_total counter
        requests_total 100
        # HELP cpu_usage CPU usage
        # TYPE cpu_usage gauge
        cpu_usage 0.75
        # HELP response_time Response time
        # TYPE response_time histogram
        response_time_bucket{le="0.005"} 0
        response_time_bucket{le="0.01"} 0
        response_time_bucket{le="0.025"} 0
        response_time_bucket{le="0.05"} 0
        response_time_bucket{le="0.1"} 1
        response_time_bucket{le="0.25"} 1
        response_time_bucket{le="0.5"} 1
        response_time_bucket{le="1.0"} 1
        response_time_bucket{le="2.5"} 1
        response_time_bucket{le="5.0"} 1
        response_time_bucket{le="10.0"} 1
        response_time_bucket{le="+Inf"} 1
        response_time_sum 0.1
        response_time_count 1
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize Prometheus exporter.

        Args:
            event_bus: Event bus for emitting metrics
        """
        super().__init__("prometheus")
        self._event_bus = event_bus
        self._type_map: Dict[Type[MetricType], str] = {
            Counter: "counter",
            Gauge: "gauge",
            Histogram: "histogram",
        }

    def format_metrics(self, metrics: Sequence[Metric]) -> str:
        """Format metrics in Prometheus text format.

        Args:
            metrics: List of metrics to format

        Returns:
            Formatted metrics string

        Raises:
            ValueError: If metric type is not supported
        """
        try:
            output: List[str] = []
            for metric in metrics:
                metric_cls = cast(Type[MetricType], type(metric))
                metric_type = self._type_map.get(metric_cls)
                if not metric_type:
                    raise ValueError(f"Unsupported metric type: {type(metric)}")

                # Add help and type
                output.append(f"# HELP {metric.name} {metric.description}")
                output.append(f"# TYPE {metric.name} {metric_type}")

                # Format metric based on type
                if isinstance(metric, (Counter, Gauge)):
                    labels = getattr(metric, "labels", {})
                    if labels:
                        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                        output.append(f"{metric.name}{{{label_str}}} {metric.value}")
                    else:
                        output.append(f"{metric.name} {metric.value}")

                elif isinstance(metric, Histogram):
                    # Add buckets
                    buckets = [
                        0.005,
                        0.01,
                        0.025,
                        0.05,
                        0.1,
                        0.25,
                        0.5,
                        1.0,
                        2.5,
                        5.0,
                        10.0,
                    ]
                    cumulative = 0
                    for bucket in buckets:
                        if metric.value <= bucket:
                            cumulative += 1
                        output.append(
                            f'{metric.name}_bucket{{le="{bucket}"}} {cumulative}'
                        )
                    # Add infinity bucket
                    output.append(f'{metric.name}_bucket{{le="+Inf"}} {cumulative}')
                    # Add sum and count
                    output.append(f"{metric.name}_sum {metric.value}")
                    output.append(f"{metric.name}_count {cumulative}")

                output.append("")  # Add blank line between metrics

            return "\n".join(output)
        except Exception as e:
            logger.error("Error formatting metrics: %s", e)
            raise

    async def export_metrics(self, metrics: Sequence[Metric]) -> None:
        """Export metrics in Prometheus format.

        Args:
            metrics: List of metrics to export

        Raises:
            ValueError: If metric type is not supported
            Exception: If exporting metrics fails
        """
        try:
            formatted = self.format_metrics(metrics)
            logger.debug("Formatted metrics: %s", formatted)

            # Emit metrics exported event
            event_data = {
                "exporter": self.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics_count": len(metrics),
            }
            await self._event_bus.publish(
                event=Event(name="metrics.exported", data=event_data)
            )
        except Exception as e:
            logger.exception("Error exporting metrics: %s", e)
            raise

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[Sequence[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics from Prometheus.

        Args:
            start_time: Start time
            end_time: End time
            metrics: Optional list of metric names to get

        Returns:
            Dictionary mapping metric names to lists of values

        Raises:
            NotImplementedError: This method is not implemented yet
        """
        raise NotImplementedError("get_metrics is not implemented yet")
