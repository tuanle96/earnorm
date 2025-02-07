# Connection Pool Module

This module provides connection pooling functionality for various database backends in the EarnORM framework.

## Overview

The pool module consists of several components:

1. Core Components
   - Base Pool (`core/`)
   - Circuit Breaker
   - Retry Policy
   - Resilience Patterns

2. Backend Implementations (`backends/`)
   - MongoDB Pool
   - Redis Pool
   - Base Pool Interface

3. Pool Management
   - Pool Factory (`factory.py`)
   - Pool Registry (`registry.py`)
   - Pool Configuration

4. Utilities (`utils/`)
   - Health Checks
   - Metrics Collection
   - Pool Statistics
   - Connection Management

## Directory Structure

```
pool/
├── __init__.py         # Package exports and configuration
├── factory.py          # Pool factory implementation
├── registry.py         # Pool registry management
├── types.py           # Type definitions
├── constants.py       # Constant values
├── core/             # Core functionality
│   ├── __init__.py
│   ├── circuit.py    # Circuit breaker
│   ├── retry.py      # Retry policies
│   └── resilience.py # Resilience patterns
├── backends/         # Database backends
│   ├── __init__.py
│   ├── base.py      # Base pool interface
│   ├── mongo.py     # MongoDB pool
│   └── redis.py     # Redis pool
├── protocols/        # Protocol definitions
│   ├── __init__.py
│   └── pool.py      # Pool protocol
└── utils/           # Utility functions
    ├── __init__.py
    ├── health.py    # Health checks
    ├── metrics.py   # Metrics collection
    └── stats.py     # Pool statistics
```

## Key Features

### 1. Pool Configuration
```python
from earnorm.pool import PoolFactory, PoolConfig

# Create pool configuration
config = PoolConfig(
    min_size=5,
    max_size=20,
    max_idle_time=60,
    connection_timeout=5,
    max_lifetime=3600,
    validate_on_borrow=True,
    test_on_return=True
)

# Create MongoDB pool
mongo_pool = PoolFactory.create(
    "mongodb",
    uri="mongodb://localhost:27017",
    database="test",
    config=config
)

# Create Redis pool
redis_pool = PoolFactory.create(
    "redis",
    uri="redis://localhost:6379",
    config=config
)
```

### 2. Pool Management
```python
from earnorm.pool import PoolRegistry

# Register custom pool
PoolRegistry.register("custom", CustomPool)

# Get pool by name
pool_class = PoolRegistry.get("mongodb")

# Check if pool exists
exists = PoolRegistry.exists("redis")
```

### 3. Connection Management
```python
# Get connection from pool
async with pool.acquire() as conn:
    # Use connection
    result = await conn.query(...)

# Health check
health = await pool.check_health()

# Get metrics
metrics = await pool.get_metrics()

# Cleanup
await pool.cleanup()
```

## Features

1. Connection Management
   - Connection pooling
   - Connection lifecycle
   - Connection validation
   - Connection cleanup
   - Connection metrics

2. Pool Features
   - Min/max pool size
   - Connection timeout
   - Idle timeout
   - Connection lifetime
   - Health checks

3. Resilience Patterns
   - Circuit breaker
   - Retry policies
   - Error handling
   - Timeout handling
   - Health monitoring

4. Metrics & Monitoring
   - Pool statistics
   - Connection metrics
   - Health status
   - Performance metrics
   - Resource usage

## Implementation Guide

### 1. Using Pool Factory

1. Basic usage:
```python
from earnorm.pool import PoolFactory

# Create MongoDB pool
mongo_pool = PoolFactory.create(
    "mongodb",
    uri="mongodb://localhost:27017",
    database="test"
)

# Create Redis pool
redis_pool = PoolFactory.create(
    "redis",
    uri="redis://localhost:6379"
)
```

2. Advanced configuration:
```python
# Custom configuration
config = PoolConfig(
    min_size=5,
    max_size=20,
    max_idle_time=60,
    connection_timeout=5,
    extra_config={
        "ssl": True,
        "auth_source": "admin"
    }
)

# Create pool with config
pool = PoolFactory.create(
    "mongodb",
    uri="mongodb://localhost:27017",
    config=config
)
```

### 2. Custom Pool Implementation

1. Create pool class:
```python
from earnorm.pool.backends import BasePool

class CustomPool(BasePool):
    async def _create_connection(self) -> Any:
        # Create new connection
        ...

    async def _destroy_connection(self, conn: Any) -> None:
        # Destroy connection
        ...

    async def _validate_connection(self, conn: Any) -> bool:
        # Validate connection
        ...
```

2. Register pool:
```python
from earnorm.pool import PoolRegistry

# Register pool
PoolRegistry.register("custom", CustomPool)

# Create custom pool
pool = PoolFactory.create("custom", **config)
```

### 3. Using Pool Features

1. Connection management:
```python
# Acquire connection
async with pool.acquire() as conn:
    # Use connection
    ...

# Get connection
conn = await pool.get()
try:
    # Use connection
    ...
finally:
    # Return connection
    await pool.put(conn)
```

2. Pool management:
```python
# Initialize pool
await pool.init()

# Check health
health = await pool.check_health()

# Get metrics
metrics = await pool.get_metrics()

# Cleanup
await pool.cleanup()

# Close pool
await pool.close()
```

## Best Practices

1. Pool Configuration
   - Set appropriate sizes
   - Configure timeouts
   - Enable validation
   - Handle cleanup
   - Monitor health

2. Connection Management
   - Use context managers
   - Handle errors
   - Validate connections
   - Monitor metrics
   - Clean up resources

3. Error Handling
   - Use circuit breaker
   - Implement retries
   - Handle timeouts
   - Log errors
   - Monitor health

4. Performance
   - Optimize pool size
   - Monitor metrics
   - Handle cleanup
   - Use connection limits
   - Implement timeouts

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
