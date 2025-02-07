# Pool Utilities

This module provides utility functions and classes for connection pooling in the EarnORM framework.

## Overview

The utils module consists of three main components:

1. Health Checks (`health.py`)
   - Connection health
   - Pool health
   - System health
   - Health metrics

2. Metrics Collection (`metrics.py`)
   - Connection metrics
   - Pool metrics
   - Performance metrics
   - Resource usage

3. Pool Statistics (`stats.py`)
   - Connection stats
   - Pool stats
   - Usage patterns
   - Performance stats

## Features

### 1. Health Checks
```python
from earnorm.pool.utils import (
    HealthCheck,
    check_pool_health,
    check_connection_health
)

# Check pool health
health = await check_pool_health(pool)
if not health.is_healthy:
    print(f"Pool unhealthy: {health.reason}")

# Custom health check
class CustomHealthCheck(HealthCheck):
    async def check(self) -> bool:
        # Perform health check
        ...
        return is_healthy
```

### 2. Metrics Collection
```python
from earnorm.pool.utils import (
    ConnectionMetrics,
    PoolMetrics,
    calculate_connection_metrics,
    calculate_pool_metrics
)

# Get connection metrics
metrics = await calculate_connection_metrics(pool)
print(f"Active connections: {metrics.active_count}")
print(f"Idle connections: {metrics.idle_count}")

# Get pool metrics
metrics = await calculate_pool_metrics(pool)
print(f"Pool utilization: {metrics.utilization}%")
print(f"Average wait time: {metrics.avg_wait_time}ms")
```

### 3. Pool Statistics
```python
from earnorm.pool.utils import (
    PoolStatistics,
    calculate_pool_statistics
)

# Get pool statistics
stats = await calculate_pool_statistics(pool)
print(f"Total connections: {stats.total_connections}")
print(f"Peak connections: {stats.peak_connections}")
print(f"Connection errors: {stats.connection_errors}")
```

## Implementation Guide

### 1. Health Checks

1. Basic health check:
```python
from earnorm.pool.utils import check_pool_health

# Check pool health
health = await check_pool_health(pool)
if health.is_healthy:
    print("Pool is healthy")
else:
    print(f"Pool is unhealthy: {health.reason}")
    print(f"Details: {health.details}")
```

2. Custom health check:
```python
from earnorm.pool.utils import HealthCheck

class DatabaseHealthCheck(HealthCheck):
    async def check(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.ping()
            return True
        except Exception as e:
            self.reason = str(e)
            return False
```

### 2. Metrics Collection

1. Connection metrics:
```python
from earnorm.pool.utils import calculate_connection_metrics

# Get metrics
metrics = await calculate_connection_metrics(pool)

# Access metrics
print(f"Total connections: {metrics.total_count}")
print(f"Active connections: {metrics.active_count}")
print(f"Idle connections: {metrics.idle_count}")
print(f"Pending requests: {metrics.pending_count}")
```

2. Pool metrics:
```python
from earnorm.pool.utils import calculate_pool_metrics

# Get metrics
metrics = await calculate_pool_metrics(pool)

# Access metrics
print(f"Pool size: {metrics.pool_size}")
print(f"Pool utilization: {metrics.utilization}%")
print(f"Average wait time: {metrics.avg_wait_time}ms")
print(f"Peak utilization: {metrics.peak_utilization}%")
```

### 3. Pool Statistics

1. Basic statistics:
```python
from earnorm.pool.utils import calculate_pool_statistics

# Get statistics
stats = await calculate_pool_statistics(pool)

# Access statistics
print(f"Total connections: {stats.total_connections}")
print(f"Peak connections: {stats.peak_connections}")
print(f"Connection errors: {stats.connection_errors}")
print(f"Average lifetime: {stats.avg_connection_lifetime}s")
```

2. Custom statistics:
```python
from earnorm.pool.utils import PoolStatistics

class CustomPoolStatistics(PoolStatistics):
    def __init__(self):
        super().__init__()
        self.custom_metric = 0
        
    async def calculate(self, pool) -> None:
        await super().calculate(pool)
        self.custom_metric = await calculate_custom_metric(pool)
```

## Best Practices

1. Health Monitoring
   - Regular health checks
   - Custom health checks
   - Error handling
   - Logging
   - Alerting

2. Metrics Collection
   - Regular collection
   - Performance impact
   - Storage strategy
   - Analysis
   - Visualization

3. Statistics
   - Collection frequency
   - Data retention
   - Analysis tools
   - Reporting
   - Optimization

4. Resource Management
   - Monitor usage
   - Set thresholds
   - Handle alerts
   - Optimize resources
   - Plan capacity

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
