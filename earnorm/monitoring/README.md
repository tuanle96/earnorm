"""Monitoring Module Documentation

The monitoring module provides a flexible and extensible system for collecting, exporting, and alerting on metrics in your application.

## Directory Structure

```
monitoring/
├── alerts/          # Alert handling and rules
├── collectors/      # Metric collectors (Redis, Network, System, etc.)
├── exporters/       # Metric exporters (Prometheus, InfluxDB, etc.)
├── metrics/         # Core metric types and protocols
├── __init__.py     # Package initialization and public API
├── container.py    # Dependency injection container
├── events.py       # Event handling
├── interfaces.py   # Core interfaces
├── lifecycle.py    # Monitor lifecycle management
└── pools.py        # Connection pool management
```

## Core Components

### Metrics

The metrics module provides the core metric types and protocols:

```python
from earnorm.monitoring.metrics import Counter, Gauge, Histogram

# Create metrics
requests = Counter("requests_total", "Total requests")
memory = Gauge("memory_usage", "Memory usage in bytes")
latency = Histogram("request_duration", "Request duration in seconds")

# Use metrics
requests.inc()
memory.set(1024)
latency.observe(0.1)
```

### Collectors

Collectors gather metrics from various sources:

```python
from earnorm.monitoring.collectors import (
    RedisCollector,
    NetworkCollector,
    SystemCollector,
    DatabaseCollector,
)

# Initialize collectors
redis_collector = RedisCollector(redis_pool)
network_collector = NetworkCollector()
system_collector = SystemCollector()
db_collector = DatabaseCollector(db_pool)

# Collect metrics
metrics = await collector.collect()
```

### Exporters

Exporters send metrics to various backends:

```python
from earnorm.monitoring.exporters import PrometheusExporter

# Initialize exporter
exporter = PrometheusExporter()

# Export metrics
await exporter.export(metrics)
```

## Usage

1. Initialize monitoring:

```python
from earnorm.monitoring import init_monitor
from earnorm.monitoring.collectors import SystemCollector
from earnorm.monitoring.exporters import PrometheusExporter

await init_monitor(
    collectors=[SystemCollector()],
    exporters=[PrometheusExporter()],
)
```

2. Use custom metrics:

```python
from earnorm.monitoring.metrics import CustomMetric

@CustomMetric(
    name="request_duration",
    description="Request duration in seconds",
    type="histogram",
)
async def handle_request():
    # Function code here
    pass
```

3. Stop monitoring:

```python
from earnorm.monitoring import stop_monitor

await stop_monitor()
```

## Best Practices

1. Use descriptive metric names and descriptions
2. Follow the naming convention: `<namespace>_<name>_<unit>`
3. Add relevant labels to metrics for better filtering
4. Keep metric cardinality under control
5. Use appropriate metric types:
   - Counter: For values that only increase
   - Gauge: For values that can go up and down
   - Histogram: For measuring distributions

## Protocol Support

The metrics module uses protocols to define the interface for metrics:

- `MetricProtocol`: Base protocol for all metrics
- `CounterProtocol`: Protocol for counter metrics
- `GaugeProtocol`: Protocol for gauge metrics
- `HistogramProtocol`: Protocol for histogram metrics

This allows for custom implementations while maintaining type safety.

## Event System

The monitoring system uses an event-based architecture:

- `metrics.collected`: Emitted when metrics are collected
- `metrics.exported`: Emitted when metrics are exported
- `alert.triggered`: Emitted when an alert is triggered

## Alert System

The alert system allows you to define rules and handlers:

```python
from earnorm.monitoring.alerts import AlertRule

rule = AlertRule(
    name="high_memory",
    condition=lambda m: m.name == "memory_usage" and m.value > 90,
    severity="critical",
)
```

## Dependencies

- Python 3.8+
- aioredis (for Redis metrics)
- psutil (for system metrics)
- prometheus_client (for Prometheus export)
- influxdb-client (for InfluxDB export)
""" 
